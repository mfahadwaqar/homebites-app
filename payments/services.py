"""Offline-only payment simulations. Nothing here contacts a payment provider."""

from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from orders.models import InventoryReservation, ListingStock, Order
from payments.models import PaymentAttempt


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


def _active_hold(order, now):
    if order.status != Order.Status.PENDING_PAYMENT:
        raise PaymentConflict("This order is not waiting for a mock payment.")
    if order.hold_expires_at is None or order.hold_expires_at <= now:
        raise PaymentConflict("The payment hold has expired. Start a new checkout.")
    if not order.slot.is_active or order.slot.ends_at <= now:
        raise PaymentConflict("The fulfillment window has ended.")
    if order.slot.order_type == order.slot.OrderType.PREORDER and (
        order.slot.preorder_deadline is None or order.slot.preorder_deadline <= now
    ):
        raise PaymentConflict("The pre-order deadline has passed.")
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
    attempt.mock_reference = f"DEMO-ORDER-{locked.pk:06d}-{attempt.pk:04d}"
    attempt.save(update_fields=["mock_reference"])
    return attempt


@transaction.atomic
def create_cash_payment_record(order):
    """Record cash due without implying that any money has changed hands."""
    locked = Order.objects.select_for_update().get(pk=_order_id(order))
    if locked.payment_method not in CASH_METHODS or locked.status in TERMINAL_ORDERS:
        raise PaymentConflict("This order cannot use simulated cash collection.")
    attempt = PaymentAttempt.objects.filter(order=locked, idempotency_key="cash-due").first()
    if attempt:
        return attempt
    if PaymentAttempt.objects.filter(order=locked).exists():
        raise PaymentConflict("This order already has a different payment record.")
    attempt = PaymentAttempt.objects.create(
        order=locked, method=locked.payment_method, amount=locked.customer_total,
        idempotency_key="cash-due", state=PaymentAttempt.State.CASH_DUE,
    )
    attempt.mock_reference = f"DEMO-CASH-{locked.pk:06d}-{attempt.pk:04d}"
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
        raise PaymentConflict("Choose a supported mock result.")
    order_id = attempt.order_id if isinstance(attempt, PaymentAttempt) else PaymentAttempt.objects.only("order_id").get(pk=attempt).order_id
    order = Order.objects.select_for_update().get(pk=order_id)
    locked = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk if isinstance(attempt, PaymentAttempt) else attempt)
    if order.buyer_id != getattr(buyer, "pk", None) or locked.order_id != order.pk:
        raise PaymentConflict("This is not your payment attempt.")
    if locked.method not in ONLINE_METHODS:
        raise PaymentConflict("Cash orders do not use the mock payment screen.")
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
    _active_hold(order, now or timezone.now())
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

    note = "Simulated payment succeeded; awaiting seller." if outcome == "succeeded" else "Simulated payment failed; stock released."
    record_order_event(order, previous_status, actor=buyer, note=note)
    return locked


@transaction.atomic
def record_cash_collection(actor, order):
    """Seller or staff records fake cash collection after seller confirmation."""
    locked = Order.objects.select_for_update().get(pk=_order_id(order))
    if getattr(actor, "pk", None) != locked.seller.user_id and not getattr(actor, "is_staff", False):
        raise PaymentConflict("Only the seller or staff can record collection.")
    if locked.payment_method not in CASH_METHODS or locked.status != Order.Status.CONFIRMED:
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
        raise PaymentConflict("This mock payment was not successful.")
    attempt.state = PaymentAttempt.State.SIMULATED_REFUNDED
    attempt.resolved_at = timezone.now()
    attempt.save(update_fields=["state", "resolved_at"])
    return attempt
