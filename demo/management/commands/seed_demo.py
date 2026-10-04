"""Build a repeatable, offline Bangkok marketplace demonstration."""

from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalog.models import COUNTRIES, FoodListing
from demo.models import DemoBuyer, DemoSlot
from fulfillment.models import DemoLocation
from orders.models import FulfillmentSlot, ListingStock
from sellers.models import SellerProfile


PICKUP_LOCATIONS = {
    "TH": "ari",
    "PK": "asok",
    "BD": "silom",
    "NP": "chatuchak",
    "IN": "bang-na",
}
PORTIONS_PER_OFFER_AND_SLOT = 20
DEMO_BUYER_USERNAME = "demo_buyer"


def _ensure_demo_buyer():
    user_model = get_user_model()
    buyer = user_model.objects.filter(username=DEMO_BUYER_USERNAME).first()
    if buyer:
        if not DemoBuyer.objects.filter(user=buyer).exists():
            raise CommandError("The demo buyer username already belongs to another account.")
        if not buyer.is_active or buyer.is_staff or buyer.is_superuser:
            raise CommandError("The marked demo buyer must be an active non-staff account.")
        return buyer
    buyer = user_model(username=DEMO_BUYER_USERNAME, display_name="Demo Buyer")
    buyer.set_unusable_password()
    buyer.save()
    DemoBuyer.objects.create(user=buyer)
    return buyer


def _slot_times(order_type, now):
    days_ahead = 1 if order_type == FulfillmentSlot.OrderType.STANDARD else 3
    hour = 12 if order_type == FulfillmentSlot.OrderType.STANDARD else 18
    day = timezone.localdate(now) + timedelta(days=days_ahead)
    starts_at = timezone.make_aware(datetime.combine(day, time(hour=hour)))
    ends_at = starts_at + timedelta(hours=2)
    deadline = starts_at - timedelta(days=1) if order_type == FulfillmentSlot.OrderType.PREORDER else None
    return starts_at, ends_at, deadline


def _current_demo_slot(seller, order_type, now):
    marker = DemoSlot.objects.select_related("slot").filter(seller=seller, order_type=order_type).first()
    if marker:
        slot = marker.slot
        if slot.is_active and slot.ends_at > now and (
            order_type == FulfillmentSlot.OrderType.STANDARD or slot.preorder_deadline > now
        ):
            return slot
        if slot.is_active:
            slot.is_active = False
            slot.save(update_fields=["is_active"])

    starts_at, ends_at, deadline = _slot_times(order_type, now)
    slot = FulfillmentSlot.objects.create(
        seller=seller, order_type=order_type, starts_at=starts_at, ends_at=ends_at,
        preorder_deadline=deadline, allows_pickup=True, allows_delivery=True,
    )
    if marker:
        marker.slot = slot
        marker.save(update_fields=["slot"])
    else:
        DemoSlot.objects.create(seller=seller, order_type=order_type, slot=slot)
    return slot


class Command(BaseCommand):
    help = "Seed the offline 50-offer Bangkok demo with five pickup points and live standard/pre-order stock."

    @transaction.atomic
    def handle(self, *args, **options):
        _ensure_demo_buyer()
        call_command("seed_catalogue", verbosity=0)
        call_command("seed_locations", verbosity=0)
        now = timezone.now()
        slots = 0
        stocks = 0

        for code, country_name in COUNTRIES.items():
            username = f"demo_seller_{country_name.lower()}"
            seller = SellerProfile.objects.get(user__username=username)
            location = DemoLocation.objects.get(code=PICKUP_LOCATIONS[code])
            if not location.is_active or location.city.casefold() != "bangkok":
                raise CommandError(f"Demo pickup location {location.code!r} must be active in Bangkok.")
            if seller.pickup_location_id is None:
                seller.pickup_location = location
                seller.save(update_fields=["pickup_location"])

            listings = list(FoodListing.objects.filter(seller=seller, dish__country_id=code))
            if len(listings) != 10:
                raise CommandError(f"Expected ten demo offers for {country_name}.")
            for order_type in (FulfillmentSlot.OrderType.STANDARD, FulfillmentSlot.OrderType.PREORDER):
                slot = _current_demo_slot(seller, order_type, now)
                slots += 1
                for listing in listings:
                    _, created = ListingStock.objects.get_or_create(
                        listing=listing, slot=slot,
                        defaults={"capacity": PORTIONS_PER_OFFER_AND_SLOT},
                    )
                    stocks += created

        self.stdout.write(self.style.SUCCESS(
            f"Demo ready: 50 offers, {slots} current slots, {stocks} new stock records. "
            "The demo buyer needs an interactive password; delivery and payment remain simulated."
        ))
