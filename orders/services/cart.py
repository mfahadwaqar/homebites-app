from django.db import transaction
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import Cart, CartItem, ListingStock


class CartError(ValueError):
    pass


class CartConflict(CartError):
    pass


def _check_listing_and_slot(buyer, listing, slot, quantity):
    now = timezone.now()
    if quantity < 1:
        raise CartError("Choose at least one portion.")
    if listing.seller.user_id == buyer.pk:
        raise CartError("You cannot order from your own storefront.")
    if not FoodListing.objects.public().filter(pk=listing.pk).exists():
        raise CartError("This offer is no longer available.")
    if slot.seller_id != listing.seller_id or not slot.is_active:
        raise CartError("Choose an active slot from this seller.")
    if slot.ends_at <= now:
        raise CartError("This fulfillment window has ended.")
    if slot.order_type == slot.OrderType.PREORDER and (
        slot.preorder_deadline is None or slot.preorder_deadline <= now
    ):
        raise CartError("The pre-order deadline has passed.")
    stock = ListingStock.objects.filter(listing=listing, slot=slot).first()
    if not stock or stock.available < quantity:
        raise CartError("Not enough portions remain for this slot.")
    return stock


@transaction.atomic
def add_to_cart(buyer, listing, slot, quantity, *, replace=False):
    if not buyer.is_authenticated:
        raise CartError("Sign in to keep a cart.")
    _check_listing_and_slot(buyer, listing, slot, quantity)
    cart, _ = Cart.objects.get_or_create(buyer=buyer)
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    has_items = cart.items.exists()
    if has_items and (cart.seller_id != listing.seller_id or cart.slot_id != slot.pk):
        if not replace:
            raise CartConflict("This item uses another seller or time slot. Confirm replacing your cart.")
        cart.items.all().delete()
        cart.destination = None
        cart.method = Cart.Method.PICKUP
    existing = cart.items.filter(listing=listing).first()
    new_quantity = quantity + (existing.quantity if existing else 0)
    _check_listing_and_slot(buyer, listing, slot, new_quantity)
    if existing:
        existing.quantity = new_quantity
        existing.acknowledged_ingredient_version = listing.ingredient_version
        existing.acknowledged_unit_price = listing.price
        existing.save(update_fields=["quantity", "acknowledged_ingredient_version", "acknowledged_unit_price"])
    else:
        CartItem.objects.create(
            cart=cart,
            listing=listing,
            quantity=quantity,
            acknowledged_ingredient_version=listing.ingredient_version,
            acknowledged_unit_price=listing.price,
        )
    cart.seller = listing.seller
    cart.slot = slot
    cart.revision += 1
    cart.save(update_fields=["seller", "slot", "method", "destination", "revision", "updated_at"])
    return cart


@transaction.atomic
def update_cart_item(buyer, item_id, quantity):
    cart = Cart.objects.select_for_update().get(buyer=buyer)
    item = cart.items.select_related("listing").get(pk=item_id)
    if quantity < 0:
        raise CartError("Quantity cannot be negative.")
    if quantity == 0:
        item.delete()
        if not cart.items.exists():
            cart.seller = None
            cart.slot = None
            cart.destination = None
            cart.method = Cart.Method.PICKUP
    else:
        _check_listing_and_slot(buyer, item.listing, cart.slot, quantity)
        item.quantity = quantity
        item.acknowledged_ingredient_version = item.listing.ingredient_version
        item.acknowledged_unit_price = item.listing.price
        item.save(update_fields=["quantity", "acknowledged_ingredient_version", "acknowledged_unit_price"])
    cart.revision += 1
    cart.save()
    return cart


@transaction.atomic
def select_fulfillment(buyer, method, destination=None):
    cart = Cart.objects.select_for_update().get(buyer=buyer)
    if not cart.items.exists() or cart.slot is None:
        raise CartError("Add an item before choosing fulfillment.")
    if method == Cart.Method.PICKUP:
        if not cart.slot.allows_pickup:
            raise CartError("Pickup is unavailable for this slot.")
        destination = None
    elif method == Cart.Method.DELIVERY:
        if not cart.slot.allows_delivery:
            raise CartError("Delivery is unavailable for this slot.")
        if destination is None or not destination.is_active or destination.city.casefold() != "bangkok":
            raise CartError("Choose a supported Bangkok demo location.")
    else:
        raise CartError("Choose pickup or simulated delivery.")
    if cart.method != method or cart.destination_id != (destination.pk if destination else None):
        cart.method = method
        cart.destination = destination
        cart.revision += 1
        cart.save(update_fields=["method", "destination", "revision", "updated_at"])
    return cart
