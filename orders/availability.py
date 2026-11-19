"""Read-only booking policy shared by discovery and purchasing."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db.models import F, Q
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import FulfillmentSlot, ListingStock


STANDARD_PREPARATION_BUFFER = timedelta(minutes=30)


def booking_cutoff(slot):
    return (slot.preorder_deadline if slot.order_type == FulfillmentSlot.OrderType.PREORDER
            else slot.ends_at - STANDARD_PREPARATION_BUFFER)


def window_problem(slot, *, at):
    if not slot.is_active:
        return "This kitchen has paused ordering for this window. Choose another window."
    if slot.ends_at <= at:
        return "This fulfillment window has ended. Choose another window."
    cutoff = booking_cutoff(slot)
    if cutoff is None or cutoff <= at:
        if slot.order_type == FulfillmentSlot.OrderType.PREORDER:
            return "The pre-order deadline has passed. Choose another window."
        return "Ordering closed 30 minutes before this window ends, to allow preparation. Choose another window."
    return None


def bookable_stocks(*, at):
    return ListingStock.objects.filter(
        listing__in=FoodListing.objects.public(), slot__seller_id=F("listing__seller_id"),
        slot__is_active=True, slot__ends_at__gt=at,
        capacity__gt=F("held") + F("committed"),
    ).filter(
        Q(slot__order_type="standard", slot__ends_at__gt=at + STANDARD_PREPARATION_BUFFER)
        | Q(slot__order_type="preorder", slot__preorder_deadline__gt=at)
    )


@dataclass(frozen=True)
class WindowAvailability:
    slot: FulfillmentSlot
    cutoff: datetime
    remaining: int


@dataclass(frozen=True)
class OfferAvailability:
    state: str
    message: str
    windows: tuple = ()

    @property
    def orderable(self):
        return bool(self.windows)

    @property
    def next_action(self):
        return "Choose a fulfillment window" if self.orderable else "Explore other food"


def evaluate_offer(listing, *, at, stocks=None):
    if listing.status != "published" or not listing.ingredients_reviewed or not listing.seller.can_sell:
        return OfferAvailability("unavailable", "This offer is not currently accepting orders.")
    stocks = list(stocks if stocks is not None else listing.stocks.select_related("slot").order_by("slot__starts_at", "pk"))
    stocks = [stock for stock in stocks if stock.slot.seller_id == listing.seller_id]
    windows = tuple(WindowAvailability(stock.slot, booking_cutoff(stock.slot), stock.available)
                    for stock in stocks if not window_problem(stock.slot, at=at) and stock.available > 0)
    if windows:
        standard = any(window.slot.order_type == "standard" for window in windows)
        return OfferAvailability("orderable" if standard else "preorder_only",
                                 "Accepting orders" if standard else "Pre-order only", windows)
    if not stocks:
        return OfferAvailability("unscheduled", "No schedule published for this dish yet.")
    if not any(stock.slot.is_active for stock in stocks):
        return OfferAvailability("paused", "Kitchen paused for these windows.")
    if any(not window_problem(stock.slot, at=at) for stock in stocks):
        return OfferAvailability("sold_out", "Sold out for the published windows.")
    active = [stock for stock in stocks if stock.slot.is_active]
    if active and all(stock.slot.order_type == "preorder" for stock in active):
        return OfferAvailability("preorder_closed", "Pre-order deadline passed. No later window is published yet.")
    return OfferAvailability("closed", "Ordering closed for the published windows. No later window is published yet.")


def attach_availability(listings, *, at=None):
    """One stock query for a page of already seller/user-selected listings."""
    listings = list(listings)
    at = at or timezone.now()
    by_listing = {listing.pk: [] for listing in listings}
    for stock in ListingStock.objects.filter(listing_id__in=by_listing).select_related("slot").order_by("slot__starts_at", "pk"):
        by_listing[stock.listing_id].append(stock)
    for listing in listings:
        listing.availability = evaluate_offer(listing, at=at, stocks=by_listing[listing.pk])
    return listings
