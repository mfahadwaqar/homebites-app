from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from fulfillment.models import DeliveryTariff
from fulfillment.services import pickup_fee, quote_delivery
from orders.models import Cart, DeliveryQuote
from orders.pricing import calculate_totals
from orders.services.cart import CartError


QUOTE_LIFETIME = timedelta(minutes=10)


def cart_subtotal(cart):
    return sum(
        (item.listing.price * item.quantity for item in cart.items.select_related("listing")),
        Decimal("0.00"),
    )


@transaction.atomic
def create_quote(buyer):
    cart = Cart.objects.select_for_update().get(buyer=buyer)
    if not cart.items.exists() or cart.seller is None or cart.slot is None:
        raise CartError("Add an item before requesting a quote.")
    subtotal = cart_subtotal(cart)
    origin = cart.seller.pickup_location
    if cart.method == Cart.Method.PICKUP:
        if not cart.slot.allows_pickup:
            raise CartError("Pickup is unavailable for this slot.")
        fee, distance, tariff_version = pickup_fee(), Decimal("0.00"), None
        destination = None
    elif cart.method == Cart.Method.DELIVERY:
        if not cart.slot.allows_delivery:
            raise CartError("Delivery is unavailable for this slot.")
        if origin is None or cart.destination is None:
            raise CartError("Select supported seller and customer demo locations.")
        estimate = quote_delivery(origin, cart.destination, subtotal)
        fee, distance, tariff_version = estimate.fee, estimate.distance_km, estimate.tariff_version
        destination = cart.destination
    else:
        raise CartError("Choose pickup or simulated delivery.")
    return DeliveryQuote.objects.create(
        cart=cart,
        cart_revision=cart.revision,
        method=cart.method,
        origin=origin,
        destination=destination,
        food_subtotal=calculate_totals(subtotal, fee).food_subtotal,
        distance_km=distance,
        fee=fee,
        tariff_version=tariff_version,
        expires_at=timezone.now() + QUOTE_LIFETIME,
    )


def valid_quote_for_cart(cart, quote, *, now=None):
    now = now or timezone.now()
    if quote is None or quote.cart_id != cart.pk or quote.expires_at <= now:
        return False
    if quote.cart_revision != cart.revision or quote.method != cart.method:
        return False
    if quote.origin_id != getattr(cart.seller, "pickup_location_id", None):
        return False
    if quote.destination_id != (cart.destination_id if cart.method == Cart.Method.DELIVERY else None):
        return False
    if quote.food_subtotal != calculate_totals(cart_subtotal(cart), quote.fee).food_subtotal:
        return False
    if cart.method == Cart.Method.PICKUP:
        return quote.fee == Decimal("0.00") and quote.tariff_version is None
    active_version = DeliveryTariff.objects.filter(is_active=True).order_by("-version").values_list("version", flat=True).first()
    return active_version is not None and quote.tariff_version == active_version
