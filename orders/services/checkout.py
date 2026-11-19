"""Transactional demo checkout and inventory reservation lifecycle."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import (
    Cart,
    DeliveryQuote,
    FulfillmentSlot,
    InventoryReservation,
    ListingStock,
    Order,
    OrderItem,
)
from orders.pricing import calculate_totals
from orders.availability import booking_cutoff, window_problem
from orders.services.cart import CartError, cart_groups
from orders.services.quotes import create_quotes, latest_valid_quote


HOLD_LIFETIME = timedelta(minutes=15)


class CheckoutConflict(CartError):
    """The cart needs a fresh review before it can become an order."""


def _lock_and_validate_items(cart, group, now):
    items = sorted(group.items, key=lambda i: i.listing_id)
    if not items:
        raise CheckoutConflict("Add a dish before checking out.")
    locked_stocks = {}
    for item in items:
        listing = item.listing
        if listing.seller.user_id == cart.buyer_id:
            raise CheckoutConflict("You cannot order from your own storefront.")
        if not FoodListing.objects.public().filter(pk=listing.pk).exists():
            raise CheckoutConflict("A dish or its seller is no longer available.")
        if (
            item.acknowledged_ingredient_version != listing.ingredient_version
            or item.acknowledged_unit_price != listing.price
        ):
            raise CheckoutConflict("Ingredients or price changed. Review your cart again.")
        stock = ListingStock.objects.select_for_update().filter(listing=listing, slot=group.slot).first()
        if stock is None or stock.available < item.quantity:
            raise CheckoutConflict("Not enough portions remain for this slot.")
        locked_stocks[item.pk] = stock
    return items, locked_stocks


def _validate_slot_and_method(cart, group, now):
    if group.seller is None or group.slot is None:
        raise CheckoutConflict("Choose a seller and fulfillment slot.")
    slot = FulfillmentSlot.objects.select_for_update().get(pk=group.slot.pk)
    if slot.seller_id != group.seller.pk:
        raise CheckoutConflict("The fulfillment slot is unavailable.")
    problem = window_problem(slot, at=now)
    if problem:
        raise CheckoutConflict(problem)
    if cart.method == Cart.Method.PICKUP and not slot.allows_pickup:
        raise CheckoutConflict("Pickup is unavailable for this slot.")
    if cart.method == Cart.Method.DELIVERY and not slot.allows_delivery:
        raise CheckoutConflict("Delivery is unavailable for this slot.")
    if cart.method not in (Cart.Method.PICKUP, Cart.Method.DELIVERY):
        raise CheckoutConflict("Choose a fulfillment method.")
    return slot


def _payment_is_compatible(cart, payment_method):
    if payment_method not in Order.PaymentMethod.values:
        return False
    if payment_method == Order.PaymentMethod.CASH_PICKUP:
        return cart.method == Cart.Method.PICKUP
    if payment_method == Order.PaymentMethod.CASH_DELIVERY:
        return cart.method == Cart.Method.DELIVERY
    return True


def _existing_orders(buyer, idempotency_key):
    from django.db.models import Q

    return list(
        Order.objects.filter(buyer=buyer)
        .filter(Q(idempotency_key=idempotency_key) | Q(idempotency_key__startswith=idempotency_key + ":"))
        .order_by("pk")
    )


def _order_key(idempotency_key, index, total):
    return idempotency_key if total == 1 else f"{idempotency_key}:{index + 1}"


@transaction.atomic
def checkout_orders(buyer, *, idempotency_key, payment_method):
    """Place one order per kitchen and window in the cart. All succeed or none do."""
    if not buyer.is_authenticated:
        raise CheckoutConflict("Sign in before checkout.")
    if not idempotency_key or len(idempotency_key) > 70:
        raise CheckoutConflict("Provide a valid checkout request key.")
    existing = _existing_orders(buyer, idempotency_key)
    if existing:
        if any(o.payment_method != payment_method for o in existing):
            raise CheckoutConflict("This checkout request used another payment method.")
        return existing

    cart = Cart.objects.select_for_update().get(buyer=buyer)
    # A concurrent retry waits for the same cart lock, then observes the first orders.
    existing = _existing_orders(buyer, idempotency_key)
    if existing:
        if any(o.payment_method != payment_method for o in existing):
            raise CheckoutConflict("This checkout request used another payment method.")
        return existing
    if not _payment_is_compatible(cart, payment_method):
        raise CheckoutConflict("Payment method does not match pickup or delivery.")

    now = timezone.now()
    groups = cart_groups(cart)
    if not groups:
        raise CheckoutConflict("Add a dish before checking out.")
    online = payment_method in (Order.PaymentMethod.MOCK_PROMPTPAY, Order.PaymentMethod.MOCK_CARD)
    from orders.services.workflow import record_order_event

    # Validate every kitchen before creating anything.
    prepared = []
    for group in groups:
        slot = _validate_slot_and_method(cart, group, now)
        items, stocks = _lock_and_validate_items(cart, group, now)
        quote = latest_valid_quote(cart, group, now=now)
        if quote is None:
            if cart.method == Cart.Method.DELIVERY:
                raise CheckoutConflict("Delivery quote changed or expired. Get a new quote.")
            create_quotes(buyer)
            quote = latest_valid_quote(cart, group, now=now)
            if quote is None:
                raise CheckoutConflict("Delivery quote changed or expired. Get a new quote.")
        expires_at = min(now + HOLD_LIFETIME, booking_cutoff(slot)) if online else None
        if online and expires_at <= now:
            raise CheckoutConflict("The payment window has closed.")
        prepared.append((group, slot, items, stocks, quote, expires_at))

    destination = cart.destination if cart.method == Cart.Method.DELIVERY else None
    orders = []
    for index, (group, slot, items, stocks, quote, expires_at) in enumerate(prepared):
        totals = calculate_totals(quote.food_subtotal, quote.fee)
        order = Order.objects.create(
            buyer=buyer,
            seller=group.seller,
            slot=slot,
            idempotency_key=_order_key(idempotency_key, index, len(prepared)),
            checkout_group=idempotency_key,
            status=Order.Status.PENDING_PAYMENT if online else Order.Status.CASH_DUE,
            payment_method=payment_method,
            fulfillment_method=cart.method,
            origin_snapshot=quote.origin.label if quote.origin else "",
            destination=destination,
            destination_snapshot=destination.label if destination else "",
            distance_km=quote.distance_km,
            tariff_version=quote.tariff_version,
            food_subtotal=totals.food_subtotal,
            delivery_fee=totals.delivery_fee,
            customer_total=totals.customer_total,
            commission_rate=totals.commission_rate,
            commission=totals.commission,
            seller_food_earnings=totals.seller_food_earnings,
            hold_expires_at=expires_at,
        )
        for item in items:
            stock = stocks[item.pk]
            listing = item.listing
            order_item = OrderItem.objects.create(
                order=order,
                listing=listing,
                dish_name_snapshot=listing.dish.name,
                country_snapshot=listing.dish.country.name,
                ingredients_snapshot=list(listing.ingredients),
                unit_price=listing.price,
                quantity=item.quantity,
                line_total=listing.price * item.quantity,
            )
            if online:
                stock.held += item.quantity
            else:
                stock.committed += item.quantity
            stock.save(update_fields=["held", "committed"])
            InventoryReservation.objects.create(
                item=order_item,
                stock=stock,
                quantity=item.quantity,
                state=InventoryReservation.State.HELD if online else InventoryReservation.State.COMMITTED,
                expires_at=expires_at,
            )
        record_order_event(order, "", actor=buyer, note="Order placed.")
        orders.append(order)
    cart.items.all().delete()
    cart.seller = None
    cart.slot = None
    cart.destination = None
    cart.method = Cart.Method.PICKUP
    cart.revision += 1
    cart.save()
    return orders


def checkout(buyer, *, idempotency_key, payment_method):
    """Place the cart as orders and return the first one (a single-kitchen cart gives exactly one)."""
    return checkout_orders(buyer, idempotency_key=idempotency_key, payment_method=payment_method)[0]


def _release_reservations(order):
    """Call with an order row lock held; safe to repeat."""
    for reservation in order.items.select_related("reservation").order_by("pk"):
        reservation = reservation.reservation
        if reservation.state == InventoryReservation.State.RELEASED:
            continue
        stock = ListingStock.objects.select_for_update().get(pk=reservation.stock_id)
        if reservation.state == InventoryReservation.State.HELD:
            stock.held -= reservation.quantity
        elif reservation.state == InventoryReservation.State.COMMITTED:
            stock.committed -= reservation.quantity
        stock.save(update_fields=["held", "committed"])
        reservation.state = InventoryReservation.State.RELEASED
        reservation.save(update_fields=["state"])


def expire_reservations(*, now=None):
    now = now or timezone.now()
    expired_ids = Order.objects.filter(
        status=Order.Status.PENDING_PAYMENT, hold_expires_at__lte=now,
    ).values_list("pk", flat=True)
    count = 0
    for order_id in expired_ids:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            if order.status != Order.Status.PENDING_PAYMENT or order.hold_expires_at > now:
                continue
            _release_reservations(order)
            previous_status = order.status
            order.status = Order.Status.EXPIRED
            order.save(update_fields=["status", "updated_at"])
            from orders.services.workflow import record_order_event

            record_order_event(order, previous_status, note="Payment hold expired.")
            count += 1
    return count


@transaction.atomic
def cancel_order(actor, order):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if actor.pk != order.buyer_id and not actor.is_staff:
        raise CheckoutConflict("Only the buyer or staff can cancel this order.")
    if order.status in (Order.Status.CANCELLED, Order.Status.EXPIRED, Order.Status.PAYMENT_FAILED):
        return order
    if order.status not in (
        Order.Status.PENDING_PAYMENT, Order.Status.CASH_DUE, Order.Status.AWAITING_SELLER,
    ):
        raise CheckoutConflict("This order can no longer be cancelled by the buyer.")
    _release_reservations(order)
    previous_status = order.status
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    from orders.services.workflow import record_order_event

    record_order_event(order, previous_status, actor=actor, note="Buyer cancelled the order.")
    from payments.services import simulate_refund

    simulate_refund(order)
    return order
