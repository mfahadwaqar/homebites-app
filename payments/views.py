from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from orders.models import Order
from payments.models import PaymentAttempt
from payments.services import PaymentConflict, create_payment_attempt, resolve_mock_payment


@login_required
def payment_page(request, order_id):
    order = get_object_or_404(Order.objects.select_related("seller"), pk=order_id, buyer=request.user)
    attempt = PaymentAttempt.objects.filter(order=order).first()
    if order.payment_method in {Order.PaymentMethod.MOCK_CARD, Order.PaymentMethod.MOCK_PROMPTPAY} and attempt is None:
        try:
            attempt = create_payment_attempt(request.user, order, idempotency_key=f"web-order-{order.pk}")
        except PaymentConflict as exc:
            messages.error(request, str(exc))
    from orders.presentation import order_presentation
    presentation = order_presentation(order, payment=attempt, at=timezone.now())
    next_unpaid = (
        Order.objects.filter(buyer=request.user, status=Order.Status.PENDING_PAYMENT)
        .exclude(pk=order.pk).order_by("pk").first()
    )
    return render(request, "payments/pay.html", {"order": order, "attempt": attempt, "presentation": presentation, "next_unpaid": next_unpaid})


@login_required
@require_POST
def payment_result(request, order_id):
    order = get_object_or_404(Order, pk=order_id, buyer=request.user)
    attempt = get_object_or_404(PaymentAttempt, order=order)
    try:
        amount = Decimal(request.POST.get("amount", ""))
        result = resolve_mock_payment(
            request.user, attempt, outcome=request.POST.get("outcome", ""), expected_amount=amount,
        )
    except (InvalidOperation, PaymentConflict) as exc:
        messages.error(request, f"The payment could not be applied: {exc}")
    else:
        if result.state == PaymentAttempt.State.SUCCEEDED:
            messages.success(request, "Payment received. The seller can now confirm your order.")
        elif result.state == PaymentAttempt.State.FAILED:
            messages.error(request, "Payment failed. Your portions were released; start a new checkout to try again.")
        else:
            messages.info(request, "Your payment is still pending.")
    return redirect("payments:pay", order_id=order.pk)
