"""Seller decisions and simulated final handoff for existing orders."""

from django.db import transaction

from orders.models import Cart, Order, OrderStatusEvent
from orders.services.checkout import _release_reservations


class WorkflowError(ValueError):
    """The actor or current order state does not permit this transition."""


def record_order_event(order, previous_status, *, actor=None, note=""):
    """Append a customer-visible event after the caller saves an order state."""
    return OrderStatusEvent.objects.create(
        order=order, previous_status=previous_status or "", status=order.status,
        actor=actor, note=note,
    )


def _lock_owned_order(actor, order_id):
    pk = order_id.pk if isinstance(order_id, Order) else order_id
    order = Order.objects.select_for_update().select_related("seller__user").get(pk=pk)
    if not getattr(actor, "is_authenticated", False) or order.seller.user_id != actor.pk:
        raise WorkflowError("Only the owning seller can manage this order.")
    return order


@transaction.atomic
def accept_order(actor, order_id):
    order = _lock_owned_order(actor, order_id)
    if order.status == Order.Status.CONFIRMED:
        return order
    if order.status not in (Order.Status.CASH_DUE, Order.Status.AWAITING_SELLER):
        raise WorkflowError("This order cannot be accepted in its current state.")
    if not order.seller.can_sell:
        raise WorkflowError("This seller is not currently approved to accept orders.")
    from payments.services import payment_is_confirmable

    if not payment_is_confirmable(order):
        raise WorkflowError("Payment is not ready for seller confirmation.")
    previous_status = order.status
    order.status = Order.Status.CONFIRMED
    order.save(update_fields=["status", "updated_at"])
    record_order_event(order, previous_status, actor=actor, note="Seller confirmed the order.")
    return order


@transaction.atomic
def reject_order(actor, order_id, *, reason):
    order = _lock_owned_order(actor, order_id)
    if order.status == Order.Status.REJECTED:
        return order
    if order.status not in (Order.Status.CASH_DUE, Order.Status.AWAITING_SELLER, Order.Status.CONFIRMED, Order.Status.PREPARING):
        raise WorkflowError("This order cannot be rejected in its current state.")
    reason = reason.strip() if isinstance(reason, str) else ""
    if not reason:
        raise WorkflowError("Explain why this order is being rejected.")
    _release_reservations(order)
    previous_status = order.status
    order.status = Order.Status.REJECTED
    order.save(update_fields=["status", "updated_at"])
    from payments.services import simulate_refund

    simulate_refund(order)
    record_order_event(order, previous_status, actor=actor, note=f"Seller rejected the order: {reason}")
    return order


def handoff_status(order):
    """The status an order must reach before the seller can complete it."""
    return Order.Status.READY if order.fulfillment_method == Cart.Method.PICKUP else Order.Status.DELIVERED


STEP_NOTES = {
    Order.Status.PREPARING: "The seller started preparing your order.",
    Order.Status.OUT_FOR_DELIVERY: "Your order is out for delivery.",
    Order.Status.DELIVERED: "Your order was delivered.",
}


@transaction.atomic
def advance_order(actor, order_id):
    """Move a confirmed order one step along: preparing, ready, out for delivery, delivered."""
    order = _lock_owned_order(actor, order_id)
    delivery = order.fulfillment_method == Cart.Method.DELIVERY
    following = {
        Order.Status.CONFIRMED: Order.Status.PREPARING,
        Order.Status.PREPARING: Order.Status.READY,
        Order.Status.OUT_FOR_DELIVERY: Order.Status.DELIVERED,
    }
    if delivery:
        following[Order.Status.READY] = Order.Status.OUT_FOR_DELIVERY
    if order.status not in following:
        raise WorkflowError("This order has no next step right now.")
    previous_status = order.status
    order.status = following[order.status]
    order.save(update_fields=["status", "updated_at"])
    if order.status == Order.Status.READY:
        note = "Your order is ready for pickup." if not delivery else "Your order is packed and ready for the courier."
    else:
        note = STEP_NOTES[order.status]
    record_order_event(order, previous_status, actor=actor, note=note)
    return order


@transaction.atomic
def complete_handoff(actor, order_id):
    order = _lock_owned_order(actor, order_id)
    if order.status == Order.Status.COMPLETED:
        return order
    if order.status != handoff_status(order):
        raise WorkflowError("Finish the earlier steps before completing this order.")
    from payments.services import payment_is_settled, record_cash_collection

    if order.payment_method in (Order.PaymentMethod.CASH_PICKUP, Order.PaymentMethod.CASH_DELIVERY):
        record_cash_collection(actor, order)
    if not payment_is_settled(order):
        raise WorkflowError("Payment must be settled before completing handoff.")
    previous_status = order.status
    order.status = Order.Status.COMPLETED
    order.save(update_fields=["status", "updated_at"])
    handoff = "pickup" if order.fulfillment_method == Cart.Method.PICKUP else "delivery"
    record_order_event(order, previous_status, actor=actor, note=f"{handoff.capitalize()} handoff recorded.")
    return order
