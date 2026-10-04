import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import FoodListing
from fulfillment.models import DemoLocation
from orders.models import Cart, CartItem, DeliveryQuote, FulfillmentSlot, Order
from orders.services.cart import CartConflict, CartError, add_to_cart, select_fulfillment, update_cart_item
from orders.services.checkout import CheckoutConflict, cancel_order, checkout, expire_reservations
from orders.services.quotes import create_quote, valid_quote_for_cart


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
        )
    except (CartError, CartConflict) as exc:
        messages.error(request, str(exc))
        return redirect("catalog:detail", pk=listing_id)
    messages.success(request, "Added to your cart. Review ingredients before checkout.")
    return redirect("orders:cart")


@login_required
def cart_detail(request):
    cart = Cart.objects.filter(buyer=request.user).select_related("seller", "slot", "destination").first()
    items = list(cart.items.select_related("listing__dish__country") if cart else [])
    quote = None
    if cart and items:
        latest = DeliveryQuote.objects.filter(cart=cart).order_by("-created_at", "-pk").first()
        if valid_quote_for_cart(cart, latest):
            quote = latest
    locations = DemoLocation.objects.filter(is_active=True, city__iexact="bangkok").order_by("label")
    return render(request, "orders/cart.html", {
        "cart": cart,
        "items": items,
        "quote": quote,
        "locations": locations,
        "checkout_key": secrets.token_urlsafe(24),
        "payment_methods": Order.PaymentMethod,
    })


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
        create_quote(request.user)
    except (CartError, Cart.DoesNotExist, ValidationError) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Simulated delivery estimate updated." if method == Cart.Method.DELIVERY else "Pickup is free.")
    return redirect("orders:cart")


@login_required
@require_POST
def checkout_view(request):
    try:
        order = checkout(
            request.user,
            idempotency_key=request.POST.get("idempotency_key", ""),
            payment_method=request.POST.get("payment_method", ""),
        )
    except (CheckoutConflict, Cart.DoesNotExist) as exc:
        messages.error(request, str(exc))
        return redirect("orders:cart")
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
    return render(request, "orders/detail.html", {"order": order, "items": order.items.all()})


@login_required
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk, buyer=request.user)
    try:
        cancel_order(request.user, order)
    except CheckoutConflict as exc:
        messages.error(request, str(exc))
    return redirect("orders:detail", pk=pk)
