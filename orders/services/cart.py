from django.db import transaction
from django.core import signing
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import Cart, CartItem, ListingStock
from orders.availability import window_problem


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
    problem = window_problem(slot, at=now)
    if problem:
        raise CartError(problem)
    stock = ListingStock.objects.filter(listing=listing, slot=slot).first()
    if not stock or stock.available < quantity:
        raise CartError("Not enough portions remain for this slot.")
    return stock


@transaction.atomic
def add_to_cart(buyer, listing, slot, quantity, *, replace=False, expected_revision=None):
    if not buyer.is_authenticated:
        raise CartError("Sign in to keep a cart.")
    _check_listing_and_slot(buyer, listing, slot, quantity)
    cart, _ = Cart.objects.get_or_create(buyer=buyer)
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    if replace and expected_revision is not None and expected_revision != cart.revision:
        raise CartConflict("Your cart changed since this confirmation. Review the replacement again.")
    if replace:
        cart.items.all().delete()
        cart.destination = None
        cart.method = Cart.Method.PICKUP
    existing = cart.items.filter(listing=listing).first()
    if existing and existing.window and existing.window.pk != slot.pk:
        raise CartError("This dish is already in your cart for another window. Remove it first to choose a different window.")
    new_quantity = quantity + (existing.quantity if existing else 0)
    _check_listing_and_slot(buyer, listing, slot, new_quantity)
    if existing:
        existing.quantity = new_quantity
        existing.slot = slot
        existing.acknowledged_ingredient_version = listing.ingredient_version
        existing.acknowledged_unit_price = listing.price
        existing.save(update_fields=["quantity", "slot", "acknowledged_ingredient_version", "acknowledged_unit_price"])
    else:
        CartItem.objects.create(
            cart=cart,
            listing=listing,
            slot=slot,
            quantity=quantity,
            acknowledged_ingredient_version=listing.ingredient_version,
            acknowledged_unit_price=listing.price,
        )
    _sync_primary(cart)
    cart.revision += 1
    cart.save(update_fields=["seller", "slot", "method", "destination", "revision", "updated_at"])
    return cart


def _sync_primary(cart):
    """Keep cart.seller/slot pointing at the first group for older code and templates."""
    first = cart.items.select_related("listing", "slot").order_by("pk").first()
    if first is None:
        cart.seller = None
        cart.slot = None
        cart.destination = None
        cart.method = Cart.Method.PICKUP
    else:
        cart.seller = first.listing.seller
        cart.slot = first.window


class CartGroup:
    """Cart items that become one order: the same kitchen and the same window."""

    def __init__(self, seller, slot, items):
        self.seller = seller
        self.slot = slot
        self.items = items

    @property
    def subtotal(self):
        from decimal import Decimal
        return sum((item.line_total for item in self.items), Decimal("0.00"))


def cart_groups(cart, items=None):
    if items is None:
        items = list(cart.items.select_related("listing__seller", "listing__dish__country", "slot", "cart__slot").order_by("pk"))
    groups = {}
    for item in items:
        key = (item.listing.seller_id, item.window.pk if item.window else None)
        if key not in groups:
            groups[key] = CartGroup(item.listing.seller, item.window, [])
        groups[key].items.append(item)
    return sorted(groups.values(), key=lambda g: (g.seller.pk, g.slot.pk if g.slot else 0))


@transaction.atomic
def update_cart_item(buyer, item_id, quantity):
    cart = Cart.objects.select_for_update().get(buyer=buyer)
    item = cart.items.select_related("listing").get(pk=item_id)
    if quantity < 0:
        raise CartError("Quantity cannot be negative.")
    if quantity == 0:
        item.delete()
        _sync_primary(cart)
    else:
        if item.acknowledged_ingredient_version != item.listing.ingredient_version or item.acknowledged_unit_price != item.listing.price:
            raise CartError("Review current ingredients and price on the dish page before updating this item.")
        _check_listing_and_slot(buyer, item.listing, item.window, quantity)
        item.quantity = quantity
        item.acknowledged_ingredient_version = item.listing.ingredient_version
        item.acknowledged_unit_price = item.listing.price
        item.save(update_fields=["quantity", "acknowledged_ingredient_version", "acknowledged_unit_price"])
    cart.revision += 1
    cart.save()
    return cart


def review_token(item):
    return signing.dumps({"item": item.pk, "buyer": item.cart.buyer_id,
                          "version": item.listing.ingredient_version, "price": str(item.listing.price)}, salt="cart-review")


@transaction.atomic
def acknowledge_cart_item(buyer, item_id, token):
    cart = Cart.objects.select_for_update().get(buyer=buyer)
    item = cart.items.select_related("listing").get(pk=item_id)
    try:
        values = signing.loads(token, salt="cart-review", max_age=900)
    except signing.BadSignature:
        raise CartError("This review link expired or is invalid. Open the dish again.") from None
    expected = {"item": item.pk, "buyer": buyer.pk, "version": item.listing.ingredient_version, "price": str(item.listing.price)}
    if values != expected:
        raise CartError("The offer changed again. Review its current ingredients and price.")
    _check_listing_and_slot(buyer, item.listing, item.window, item.quantity)
    item.acknowledged_ingredient_version = item.listing.ingredient_version
    item.acknowledged_unit_price = item.listing.price
    item.save(update_fields=["acknowledged_ingredient_version", "acknowledged_unit_price"])
    cart.revision += 1
    cart.save(update_fields=["revision", "updated_at"])
    return cart


def cart_problems(cart, items, *, at):
    if not cart or not items:
        return []
    problems = []
    public_ids = set(FoodListing.objects.public().filter(pk__in=[item.listing_id for item in items]).values_list("pk", flat=True))
    for group in cart_groups(cart, items):
        kitchen = group.seller.storefront_name
        slot = group.slot
        if slot is None:
            problems.append("Choose a fulfillment window again from the dish page.")
            continue
        problem = window_problem(slot, at=at)
        if problem:
            problems.append(f"{kitchen}: {problem}")
        stock = {row.listing_id: row for row in ListingStock.objects.filter(slot=slot, listing_id__in=public_ids)}
        for item in group.items:
            name = item.listing.dish.name
            if item.listing_id not in public_ids:
                problems.append(f"{name} or its kitchen is no longer accepting orders. Remove it or explore other food.")
            elif item.listing_id not in stock or stock[item.listing_id].available < item.quantity:
                problems.append(f"Not enough portions remain for {name}. Reduce the quantity or choose another window.")
            if item.acknowledged_ingredient_version != item.listing.ingredient_version or item.acknowledged_unit_price != item.listing.price:
                problems.append(f"Ingredients or price changed for {name}. Review the current offer before checkout.")
        if cart.method == "pickup" and not slot.allows_pickup:
            problems.append(f"{kitchen}: this window is delivery-only. Select delivery and calculate the delivery price.")
        if cart.method == "delivery" and not slot.allows_delivery:
            problems.append(f"{kitchen}: this window is pickup-only. Select free pickup.")
    return problems


@transaction.atomic
def select_fulfillment(buyer, method, destination=None):
    cart = Cart.objects.select_for_update().get(buyer=buyer)
    if not cart.items.exists():
        raise CartError("Add an item before choosing fulfillment.")
    groups = cart_groups(cart)
    if any(g.slot is None for g in groups):
        raise CartError("Add an item before choosing fulfillment.")
    if method == Cart.Method.PICKUP:
        for g in groups:
            if not g.slot.allows_pickup:
                raise CartError("Pickup is unavailable for this slot.")
        destination = None
    elif method == Cart.Method.DELIVERY:
        for g in groups:
            if not g.slot.allows_delivery:
                raise CartError("Delivery is unavailable for this slot.")
        if destination is None or not destination.is_active or destination.city.casefold() != "bangkok":
            raise CartError("Choose a supported Bangkok demo location.")
    else:
        raise CartError("Choose pickup or delivery.")
    if cart.method != method or cart.destination_id != (destination.pk if destination else None):
        cart.method = method
        cart.destination = destination
        cart.revision += 1
        cart.save(update_fields=["method", "destination", "revision", "updated_at"])
    return cart
