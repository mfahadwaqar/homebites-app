from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from fulfillment.models import DeliveryTariff
from fulfillment.services import pickup_fee, quote_delivery
from orders.models import Cart, DeliveryQuote
from orders.pricing import calculate_totals
from orders.services.cart import CartError, cart_groups


QUOTE_LIFETIME = timedelta(minutes=10)


def cart_subtotal(cart, group=None):
    if group is not None:
        return group.subtotal
    return sum(
        (item.listing.price * item.quantity for item in cart.items.select_related("listing")),
        Decimal("0.00"),
    )


def _quote_group(cart, group):
    subtotal = cart_subtotal(cart, group)
    origin = group.seller.pickup_location
    if cart.method == Cart.Method.PICKUP:
        if not group.slot.allows_pickup:
            raise CartError("Pickup is unavailable for this slot.")
        fee, distance, tariff_version = pickup_fee(), Decimal("0.00"), None
        destination = None
    elif cart.method == Cart.Method.DELIVERY:
        if not group.slot.allows_delivery:
            raise CartError("Delivery is unavailable for this slot.")
        if origin is None or cart.destination is None:
            raise CartError("Select supported seller and customer demo locations.")
        estimate = quote_delivery(origin, cart.destination, subtotal)
        fee, distance, tariff_version = estimate.fee, estimate.distance_km, estimate.tariff_version
        destination = cart.destination
    else:
        raise CartError("Choose pickup or delivery.")
    return DeliveryQuote.objects.create(
        cart=cart,
        cart_revision=cart.revision,
        seller=group.seller,
        method=cart.method,
        origin=origin,
        destination=destination,
        food_subtotal=calculate_totals(subtotal, fee).food_subtotal,
        distance_km=distance,
        fee=fee,
        tariff_version=tariff_version,
        expires_at=timezone.now() + QUOTE_LIFETIME,
    )


@transaction.atomic
def create_quotes(buyer):
    """Create a fresh price for every kitchen in the cart; returns them in cart-group order."""
    cart = Cart.objects.select_for_update().get(buyer=buyer)
    groups = cart_groups(cart)
    if not groups or any(g.slot is None for g in groups):
        raise CartError("Add an item before requesting a quote.")
    return [_quote_group(cart, g) for g in groups]


def create_quote(buyer):
    """Create quotes for the cart and return the first one (single-kitchen carts have one)."""
    return create_quotes(buyer)[0]


def _find_group(cart, quote, group):
    if group is not None:
        return group
    groups = cart_groups(cart)
    for g in groups:
        if quote is not None and quote.seller_id is not None and g.seller.pk == quote.seller_id:
            return g
    return groups[0] if groups else None


def valid_quote_for_cart(cart, quote, *, now=None, group=None):
    now = now or timezone.now()
    if quote is None or quote.cart_id != cart.pk or quote.expires_at <= now:
        return False
    group = _find_group(cart, quote, group)
    if group is None:
        return False
    if quote.seller_id is not None and quote.seller_id != group.seller.pk:
        return False
    if quote.cart_revision != cart.revision or quote.method != cart.method:
        return False
    if quote.origin_id != getattr(group.seller, "pickup_location_id", None):
        return False
    if quote.destination_id != (cart.destination_id if cart.method == Cart.Method.DELIVERY else None):
        return False
    if quote.food_subtotal != calculate_totals(cart_subtotal(cart, group), quote.fee).food_subtotal:
        return False
    if cart.method == Cart.Method.PICKUP:
        return quote.fee == Decimal("0.00") and quote.tariff_version is None
    active_version = DeliveryTariff.objects.filter(is_active=True).order_by("-version").values_list("version", flat=True).first()
    return active_version is not None and quote.tariff_version == active_version


def latest_valid_quote(cart, group, *, now=None):
    """Newest quote for this kitchen that still matches the cart, or None."""
    candidates = DeliveryQuote.objects.filter(cart=cart).order_by("-created_at", "-pk")
    for quote in candidates[:20]:
        if quote.seller_id not in (None, group.seller.pk):
            continue
        return quote if valid_quote_for_cart(cart, quote, now=now, group=group) else None
    return None
