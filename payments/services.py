"""Offline-only payment simulations. Nothing here contacts a payment provider."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from orders.models import InventoryReservation, ListingStock, Order
from payments.models import PaymentAttempt
from orders.availability import window_problem


ONLINE_METHODS = {Order.PaymentMethod.MOCK_PROMPTPAY, Order.PaymentMethod.MOCK_CARD}
CASH_METHODS = {Order.PaymentMethod.CASH_PICKUP, Order.PaymentMethod.CASH_DELIVERY}
TERMINAL_ORDERS = {
    Order.Status.EXPIRED, Order.Status.PAYMENT_FAILED, Order.Status.CANCELLED,
    Order.Status.REJECTED, Order.Status.COMPLETED,
}


class PaymentConflict(ValueError):
    """The requested simulated payment transition is not permitted."""


def _order_id(order):
    return order.pk if isinstance(order, Order) else order


def _active_hold(order, now, *, check_window=True):
    if order.status != Order.Status.PENDING_PAYMENT:
        raise PaymentConflict("This order is not waiting for a payment.")
    if order.hold_expires_at is None or order.hold_expires_at <= now:
        raise PaymentConflict("The payment hold has expired. Start a new checkout.")
    problem = window_problem(order.slot, at=now) if check_window else None
    if problem:
        raise PaymentConflict(problem)
    reservations = list(
        InventoryReservation.objects.filter(item__order=order).order_by("stock_id", "pk")
    )
    if not reservations or any(r.state != InventoryReservation.State.HELD for r in reservations):
        raise PaymentConflict("The order no longer has a valid stock hold.")


@transaction.atomic
def create_payment_attempt(buyer, order, *, idempotency_key, now=None):
    """Create or return one fake online-payment attempt for a payable order."""
    if not idempotency_key or len(idempotency_key) > 80:
        raise PaymentConflict("Provide a payment attempt key.")
    locked = Order.objects.select_for_update().get(pk=_order_id(order))
    if locked.buyer_id != getattr(buyer, "pk", None):
        raise PaymentConflict("This is not your order.")
    if locked.payment_method not in ONLINE_METHODS:
        raise PaymentConflict("This order uses a cash method.")
    existing = PaymentAttempt.objects.filter(order=locked, idempotency_key=idempotency_key).first()
    if existing:
        return existing
    if PaymentAttempt.objects.filter(order=locked).exists():
        raise PaymentConflict("This order already has a payment attempt.")
    _active_hold(locked, now or timezone.now())
    attempt = PaymentAttempt.objects.create(
        order=locked, method=locked.payment_method, amount=locked.customer_total,
        idempotency_key=idempotency_key, state=PaymentAttempt.State.PENDING,
    )
    attempt.mock_reference = f"HB-ORDER-{locked.pk:06d}-{attempt.pk:04d}"
    attempt.save(update_fields=["mock_reference"])
    return attempt


@transaction.atomic
def create_cash_payment_record(order):
    """Record cash due without implying that any money has changed hands."""
    locked = Order.objects.select_for_update().get(pk=_order_id(order))
    if locked.payment_method not in CASH_METHODS or locked.status in TERMINAL_ORDERS:
        raise PaymentConflict("This order cannot use cash collection.")
    attempt = PaymentAttempt.objects.filter(order=locked, idempotency_key="cash-due").first()
    if attempt:
        return attempt
    if PaymentAttempt.objects.filter(order=locked).exists():
        raise PaymentConflict("This order already has a different payment record.")
    attempt = PaymentAttempt.objects.create(
        order=locked, method=locked.payment_method, amount=locked.customer_total,
        idempotency_key="cash-due", state=PaymentAttempt.State.CASH_DUE,
    )
    attempt.mock_reference = f"HB-CASH-{locked.pk:06d}-{attempt.pk:04d}"
    attempt.save(update_fields=["mock_reference"])
    return attempt


def _move_reservations(order, *, success):
    """Called only while the order row is locked, in the same transaction."""
    reservations = list(
        InventoryReservation.objects.select_for_update()
        .filter(item__order=order).order_by("stock_id", "pk")
    )
    if not reservations or any(r.state != InventoryReservation.State.HELD for r in reservations):
        raise PaymentConflict("The stock hold is no longer available.")
    for reservation in reservations:
        stock = ListingStock.objects.select_for_update().get(pk=reservation.stock_id)
        if stock.held < reservation.quantity:
            raise PaymentConflict("The stock hold is inconsistent.")
        stock.held -= reservation.quantity
        if success:
            stock.committed += reservation.quantity
            reservation.state = InventoryReservation.State.COMMITTED
        else:
            reservation.state = InventoryReservation.State.RELEASED
        stock.save(update_fields=["held", "committed"])
        reservation.save(update_fields=["state"])


@transaction.atomic
def resolve_mock_payment(buyer, attempt, *, outcome, expected_amount, now=None):
    """Apply a fake result exactly once; a late or contradictory result is rejected."""
    if outcome not in {"pending", "succeeded", "failed"}:
        raise PaymentConflict("Choose a supported payment result.")
    order_id = attempt.order_id if isinstance(attempt, PaymentAttempt) else PaymentAttempt.objects.only("order_id").get(pk=attempt).order_id
    order = Order.objects.select_for_update().get(pk=order_id)
    locked = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk if isinstance(attempt, PaymentAttempt) else attempt)
    if order.buyer_id != getattr(buyer, "pk", None) or locked.order_id != order.pk:
        raise PaymentConflict("This is not your payment attempt.")
    if locked.method not in ONLINE_METHODS:
        raise PaymentConflict("Cash orders do not use the payment screen.")
    try:
        submitted_amount = Decimal(str(expected_amount))
    except (InvalidOperation, ValueError):
        raise PaymentConflict("The payment amount is invalid.") from None
    if locked.amount != order.customer_total or locked.amount != submitted_amount:
        raise PaymentConflict("The payment amount does not match the order.")
    if locked.state in {PaymentAttempt.State.SUCCEEDED, PaymentAttempt.State.FAILED}:
        if locked.state == outcome:
            return locked
        raise PaymentConflict("This payment result was already finalized differently.")
    if locked.state != PaymentAttempt.State.PENDING:
        raise PaymentConflict("This payment is not pending.")
    _active_hold(order, now or timezone.now(), check_window=False)
    if outcome == "pending":
        return locked
    _move_reservations(order, success=outcome == "succeeded")
    previous_status = order.status
    order.status = Order.Status.AWAITING_SELLER if outcome == "succeeded" else Order.Status.PAYMENT_FAILED
    order.save(update_fields=["status", "updated_at"])
    locked.state = PaymentAttempt.State.SUCCEEDED if outcome == "succeeded" else PaymentAttempt.State.FAILED
    locked.resolved_at = now or timezone.now()
    locked.save(update_fields=["state", "resolved_at"])
    from orders.services.workflow import record_order_event

    note = "Payment received; awaiting seller." if outcome == "succeeded" else "Payment failed; stock released."
    record_order_event(order, previous_status, actor=buyer, note=note)
    return locked


@transaction.atomic
def record_cash_collection(actor, order):
    """Seller or staff records fake cash collection after seller confirmation."""
    locked = Order.objects.select_for_update().get(pk=_order_id(order))
    if getattr(actor, "pk", None) != locked.seller.user_id and not getattr(actor, "is_staff", False):
        raise PaymentConflict("Only the seller or staff can record collection.")
    collectable = (Order.Status.CONFIRMED, Order.Status.PREPARING, Order.Status.READY,
                   Order.Status.OUT_FOR_DELIVERY, Order.Status.DELIVERED)
    if locked.payment_method not in CASH_METHODS or locked.status not in collectable:
        raise PaymentConflict("Cash can only be collected for a confirmed cash order.")
    attempt = PaymentAttempt.objects.select_for_update().filter(order=locked).first()
    if attempt is None:
        attempt = create_cash_payment_record(locked)
    if attempt.state == PaymentAttempt.State.CASH_COLLECTED:
        return attempt
    if attempt.state != PaymentAttempt.State.CASH_DUE or attempt.amount != locked.customer_total:
        raise PaymentConflict("This cash record cannot be collected.")
    attempt.state = PaymentAttempt.State.CASH_COLLECTED
    attempt.resolved_at = timezone.now()
    attempt.save(update_fields=["state", "resolved_at"])
    return attempt


def payment_is_confirmable(order):
    """Seller may accept a successful online simulation or a cash-due order."""
    if order.payment_method in ONLINE_METHODS:
        return order.payment_attempts.filter(state=PaymentAttempt.State.SUCCEEDED, amount=order.customer_total).exists()
    if order.payment_method in CASH_METHODS:
        if order.status == Order.Status.CASH_DUE:
            return True
        return order.payment_attempts.filter(
            state__in=[PaymentAttempt.State.CASH_DUE, PaymentAttempt.State.CASH_COLLECTED],
            amount=order.customer_total,
        ).exists()
    return False


def payment_is_settled(order):
    """Only simulated success or recorded fake cash permits completion."""
    return order.payment_attempts.filter(
        state__in=[PaymentAttempt.State.SUCCEEDED, PaymentAttempt.State.CASH_COLLECTED],
        amount=order.customer_total,
    ).exists()


@transaction.atomic
def simulate_refund(order):
    """Mark a successful mock payment refunded after an eligible order cancellation."""
    locked = Order.objects.select_for_update().get(pk=_order_id(order))
    if locked.status not in {Order.Status.CANCELLED, Order.Status.REJECTED}:
        raise PaymentConflict("Only a cancelled or rejected order can be refunded.")
    attempt = PaymentAttempt.objects.select_for_update().filter(order=locked).first()
    if attempt is None or attempt.state in {
        PaymentAttempt.State.CASH_DUE, PaymentAttempt.State.CASH_COLLECTED,
        PaymentAttempt.State.FAILED, PaymentAttempt.State.CANCELLED,
    }:
        return attempt
    if attempt.state == PaymentAttempt.State.PENDING:
        attempt.state = PaymentAttempt.State.CANCELLED
        attempt.resolved_at = timezone.now()
        attempt.save(update_fields=["state", "resolved_at"])
        return attempt
    if attempt.state == PaymentAttempt.State.SIMULATED_REFUNDED:
        return attempt
    if attempt.state != PaymentAttempt.State.SUCCEEDED:
        raise PaymentConflict("This payment was not successful.")
    attempt.state = PaymentAttempt.State.SIMULATED_REFUNDED
    attempt.resolved_at = timezone.now()
    attempt.save(update_fields=["state", "resolved_at"])
    return attempt


def checkout_group_orders(order):
    """Every order placed in the same checkout (just this order for older or single orders)."""
    order_id = _order_id(order)
    base = Order.objects.get(pk=order_id)
    if not base.checkout_group:
        return [base]
    return list(Order.objects.filter(buyer_id=base.buyer_id, checkout_group=base.checkout_group).order_by("pk"))


@transaction.atomic
def resolve_group_payment(buyer, order, *, outcome, expected_total, now=None):
    """Settle one payment for a whole checkout. Each kitchen's order keeps its own payment
    record, which is that kitchen's share of the money, so one payment covers every kitchen."""
    orders = checkout_group_orders(order)
    if any(o.buyer_id != getattr(buyer, "pk", None) for o in orders):
        raise PaymentConflict("This is not your payment.")
    try:
        submitted = Decimal(str(expected_total))
    except (InvalidOperation, ValueError):
        raise PaymentConflict("The payment amount is invalid.") from None
    attempts = []
    for member in orders:
        attempt = PaymentAttempt.objects.filter(order=member).order_by("-pk").first()
        if attempt is None:
            attempt = create_payment_attempt(buyer, member, idempotency_key=f"web-order-{member.pk}", now=now)
        attempts.append(attempt)
    pending = [a for a in attempts if a.state == PaymentAttempt.State.PENDING]
    if pending and submitted != sum((a.amount for a in pending), Decimal("0.00")):
        raise PaymentConflict("The payment amount does not match the order.")
    results = []
    for attempt in attempts:
        if attempt.state == PaymentAttempt.State.PENDING:
            results.append(resolve_mock_payment(buyer, attempt, outcome=outcome, expected_amount=attempt.amount, now=now))
        else:
            results.append(attempt)
    return results
