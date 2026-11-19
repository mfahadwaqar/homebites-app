from decimal import Decimal
import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from catalog.models import FoodListing
from fulfillment.models import DemoLocation, DeliveryTariff
from orders.models import Cart, CartItem, DeliveryQuote, FulfillmentSlot, Order
from orders.services.cart import CartConflict, CartError, add_to_cart, cart_groups, select_fulfillment, update_cart_item
from orders.services.checkout import CheckoutConflict, cancel_order, checkout_orders, expire_reservations
from orders.services.quotes import create_quotes, latest_valid_quote
from orders.services.cart import acknowledge_cart_item, cart_problems
from orders.availability import booking_cutoff
from orders.pricing import calculate_totals


def _int_value(raw, default=0):
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


@login_required
@require_POST
def cart_add(request, listing_id):
    expire_reservations()
    listing = get_object_or_404(FoodListing.objects.public(), pk=listing_id)
    slot = get_object_or_404(FulfillmentSlot, pk=_int_value(request.POST.get("slot")))
    quantity = _int_value(request.POST.get("quantity"))
    try:
        add_to_cart(
            request.user, listing, slot, quantity,
            replace=request.POST.get("replace") == "yes",
            expected_revision=_int_value(request.POST.get("expected_revision"), -1) if request.POST.get("replace") == "yes" else None,
        )
    except CartConflict as exc:
        cart = Cart.objects.get(buyer=request.user)
        return render(request, "orders/cart_replace.html", {"cart": cart, "listing": listing, "slot": slot, "quantity": quantity, "reason": str(exc)})
    except CartError as exc:
        messages.error(request, str(exc))
        return redirect("catalog:detail", pk=listing_id)
    messages.success(request, "Added to your cart. Review ingredients before checkout.")
    return redirect("orders:cart")


@login_required
def cart_detail(request):
    cart = Cart.objects.filter(buyer=request.user).select_related("seller", "slot", "destination").first()
    items = list(cart.items.select_related("listing__dish__country", "listing__seller", "slot") if cart else [])
    now = timezone.now()
    groups = []
    all_quoted = True
    food_total = delivery_total = Decimal("0.00")
    if cart and items:
        for group in cart_groups(cart, items):
            quote = latest_valid_quote(cart, group, now=now)
            group.quote = quote
            group.cutoff = booking_cutoff(group.slot) if group.slot else None
            group.totals = calculate_totals(quote.food_subtotal, quote.fee) if quote else None
            if quote:
                food_total += quote.food_subtotal
                delivery_total += quote.fee
            else:
                food_total += group.subtotal
                if cart.method == Cart.Method.DELIVERY:
                    all_quoted = False
            groups.append(group)
    grand_total = food_total + delivery_total
    first_quote = groups[0].quote if groups else None
    locations = DemoLocation.objects.filter(is_active=True, city__iexact="bangkok").order_by("label")
    return render(request, "orders/cart.html", {
        "cart": cart,
        "items": items,
        "groups": groups,
        "multi": len(groups) > 1,
        "quote": first_quote,
        "all_quoted": all_quoted,
        "food_total": food_total,
        "delivery_total": delivery_total,
        "grand_total": grand_total,
        "locations": locations,
        "checkout_key": secrets.token_urlsafe(24),
        "payment_methods": Order.PaymentMethod,
        "cart_problems": cart_problems(cart, items, at=now),
        "all_pickup": all(g.slot.allows_pickup for g in groups) if groups else True,
        "all_delivery": all(g.slot.allows_delivery for g in groups) if groups else True,
        "tariff": DeliveryTariff.objects.filter(is_active=True).order_by("-version").first(),
    })


@login_required
@require_POST
def cart_acknowledge(request, item_id):
    try:
        acknowledge_cart_item(request.user, item_id, request.POST.get("review_token", ""))
    except (CartError, Cart.DoesNotExist, CartItem.DoesNotExist) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Current ingredients and price confirmed. Review your total before checkout.")
    return redirect("orders:cart")


@login_required
@require_POST
def cart_update(request, item_id):
    try:
        update_cart_item(request.user, item_id, _int_value(request.POST.get("quantity"), -1))
    except (CartError, CartConflict, Cart.DoesNotExist, CartItem.DoesNotExist) as exc:
        messages.error(request, str(exc))
    return redirect("orders:cart")


@login_required
@require_POST
def cart_quote(request):
    method = request.POST.get("method")
    destination = None
    if method == Cart.Method.DELIVERY:
        destination = DemoLocation.objects.filter(pk=_int_value(request.POST.get("destination"))).first()
    try:
        select_fulfillment(request.user, method, destination)
        create_quotes(request.user)
    except (CartError, Cart.DoesNotExist, ValidationError) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Delivery price updated." if method == Cart.Method.DELIVERY else "Pickup is free.")
    return redirect("orders:cart")


@login_required
@require_POST
def checkout_view(request):
    try:
        orders = checkout_orders(
            request.user,
            idempotency_key=request.POST.get("idempotency_key", ""),
            payment_method=request.POST.get("payment_method", ""),
        )
    except (CheckoutConflict, Cart.DoesNotExist) as exc:
        messages.error(request, str(exc))
        return redirect("orders:cart")
    online = (Order.PaymentMethod.MOCK_CARD, Order.PaymentMethod.MOCK_PROMPTPAY)
    pending = [o for o in orders if o.payment_method in online and o.status == Order.Status.PENDING_PAYMENT]
    if len(orders) > 1:
        messages.success(request, f"{len(orders)} orders placed, one for each kitchen.")
        if pending:
            messages.info(request, "Pay once for all of them below. Your payment is split between the kitchens automatically.")
            return redirect("payments:pay", order_id=pending[0].pk)
        return redirect("orders:list")
    order = orders[0]
    if pending:
        return redirect("payments:pay", order_id=order.pk)
    return redirect("orders:detail", pk=order.pk)


@login_required
def order_list(request):
    orders = Order.objects.filter(buyer=request.user).select_related("seller", "slot")
    return render(request, "orders/list.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("seller", "slot", "destination"), pk=pk, buyer=request.user,
    )
    from orders.presentation import order_presentation
    from reviews.models import Review
    review = Review.objects.filter(order=order).first()
    return render(request, "orders/detail.html", {"order": order, "items": order.items.all(),
        "presentation": order_presentation(order, payment=order.payment_attempts.first(), at=timezone.now()),
        "review": review, "can_review": order.status == "completed" and review is None})


@login_required
def order_receipt(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("seller", "slot", "destination"), pk=pk, buyer=request.user,
    )
    from orders.presentation import order_presentation
    attempt = order.payment_attempts.first()
    return render(request, "orders/receipt.html", {
        "order": order, "items": order.items.all(), "reference": attempt.mock_reference if attempt else "",
        "presentation": order_presentation(order, payment=attempt, at=timezone.now()),
    })


@login_required
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    targets = [order]
    if order.checkout_group and order.status == Order.Status.PENDING_PAYMENT:
        targets = list(Order.objects.filter(
            buyer=request.user, checkout_group=order.checkout_group, status=Order.Status.PENDING_PAYMENT,
        ).order_by("pk"))
    try:
        for target in targets:
            cancel_order(request.user, target)
    except CheckoutConflict as exc:
        messages.error(request, str(exc))
    return redirect("orders:detail", pk=pk)
