from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from orders.models import Order
from payments.models import PaymentAttempt
from payments.services import (
    PaymentConflict, checkout_group_orders, create_payment_attempt, resolve_group_payment,
)


@login_required
def payment_page(request, order_id):
    requested = get_object_or_404(Order.objects.select_related("seller"), pk=order_id, buyer=request.user)
    group = checkout_group_orders(requested)
    order = group[0]
    for member in group:
        if member.payment_method in {Order.PaymentMethod.MOCK_CARD, Order.PaymentMethod.MOCK_PROMPTPAY} \
                and not PaymentAttempt.objects.filter(order=member).exists() \
                and member.status == Order.Status.PENDING_PAYMENT:
            try:
                create_payment_attempt(request.user, member, idempotency_key=f"web-order-{member.pk}")
            except PaymentConflict as exc:
                messages.error(request, str(exc))
    attempt = PaymentAttempt.objects.filter(order=order).first()
    from orders.presentation import order_presentation
    presentation = order_presentation(order, payment=attempt, at=timezone.now())
    group_total = sum((m.customer_total for m in group), Decimal("0.00"))
    expires = [m.hold_expires_at for m in group if m.hold_expires_at and m.status == Order.Status.PENDING_PAYMENT]
    return render(request, "payments/pay.html", {
        "order": order, "attempt": attempt, "presentation": presentation,
        "group": group, "multi": len(group) > 1, "group_total": group_total,
        "hold_expires_at": min(expires) if expires else order.hold_expires_at,
    })


@login_required
@require_POST
def payment_result(request, order_id):
    order = get_object_or_404(Order, pk=order_id, buyer=request.user)
    try:
        amount = Decimal(request.POST.get("amount", ""))
        results = resolve_group_payment(
            request.user, order, outcome=request.POST.get("outcome", ""), expected_total=amount,
        )
    except (InvalidOperation, PaymentConflict) as exc:
        messages.error(request, f"The payment could not be applied: {exc}")
    else:
        states = {r.state for r in results}
        if PaymentAttempt.State.SUCCEEDED in states:
            messages.success(request, "Payment received. The seller can now confirm your order." if len(results) == 1
                             else "Payment received. Each kitchen can now confirm its order.")
        elif PaymentAttempt.State.FAILED in states:
            messages.error(request, "Payment failed. Your portions were released; start a new checkout to try again.")
        else:
            messages.info(request, "Your payment is still pending.")
    return redirect("payments:pay", order_id=order.pk)
