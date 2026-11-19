"""Customer-facing explanations of existing order and payment records."""
from orders.availability import window_problem


def order_presentation(order, *, payment=None, at):
    online = order.payment_method in ("mock_card", "mock_promptpay")
    hold_open = (order.status == "pending_payment" and order.hold_expires_at is not None
                 and order.hold_expires_at > at and not window_problem(order.slot, at=at))
    if payment:
        payment_label = payment.get_state_display()
    elif not online and order.status in ("cash_due", "confirmed", "preparing", "ready", "out_for_delivery", "delivered"):
        payment_label = "Cash due at pickup" if order.fulfillment_method == "pickup" else "Cash due at delivery"
    else:
        payment_label = "No successful payment recorded"
    if order.status == "pending_payment" and not hold_open:
        payment_label = "Payment window closed"
    next_actions = {
        "pending_payment": "Complete your payment before the hold expires." if hold_open else "The hold expired. Choose the dishes again and start a fresh checkout.",
        "payment_failed": "Payment failed and portions were released. Choose the dishes again for a new checkout.",
        "cash_due": "The seller must confirm your order. Cash is due at handoff.",
        "awaiting_seller": "The seller must confirm your order. Payment received.",
        "confirmed": "The seller confirmed your order and will start preparing it soon.",
        "preparing": "The seller is preparing your food.",
        "ready": "Your order is ready for pickup." if order.fulfillment_method == "pickup" else "Your order is packed and will go out for delivery shortly.",
        "out_for_delivery": "Your order is on its way.",
        "delivered": "Your order has been delivered. The seller will complete it shortly.",
        "completed": "The handoff is complete. You may review this order once.",
        "expired": "The hold expired and portions were released. Start a fresh checkout if food is still available.",
        "cancelled": "This order was cancelled. Any payment is marked refunded.",
        "rejected": "The seller rejected this order. See the timeline for the reason and refund record.",
    }
    fulfillment_label = {"confirmed": "Confirmed", "preparing": "Being prepared", "ready": "Ready for pickup" if order.fulfillment_method == "pickup" else "Ready for delivery",
                         "out_for_delivery": "Out for delivery", "delivered": "Delivered", "completed": "Completed",
                         "cancelled": "Cancelled", "rejected": "Rejected", "expired": "Not scheduled — checkout expired",
                         "payment_failed": "Not scheduled — payment failed"}.get(order.status, "Awaiting seller confirmation")
    if order.status == "pending_payment":
        fulfillment_label = "Awaiting payment before seller confirmation"
    return {"steps": order_steps(order), "payment_label": payment_label, "fulfillment_label": fulfillment_label,
            "next_action": next_actions.get(order.status, "View the order timeline."), "can_pay": bool(hold_open)}


def order_steps(order):
    """Progress line for the order page, following the proposal's status chain."""
    online = order.payment_method in ("mock_card", "mock_promptpay")
    pickup = order.fulfillment_method == "pickup"
    labels = ["Order placed", "Payment" if online else "Cash due", "Seller confirms", "Preparing"]
    labels += ["Ready for pickup", "Completed"] if pickup else ["Ready", "Out for delivery", "Delivered", "Completed"]
    last = len(labels) - 1
    # status -> (steps done, step in progress or stopped)
    reached = {
        "pending_payment": (1, 1), "awaiting_seller": (2, 2), "cash_due": (2, 2), "confirmed": (3, None),
        "preparing": (3, 3), "ready": (4, 4),
        "out_for_delivery": (5, 5), "delivered": (6, None),
    }
    stopped = {"payment_failed": (1, 1), "expired": (1, 1), "cancelled": (1, 1), "rejected": (2, 2)}
    if order.status == "completed":
        done, current, is_stopped = len(labels), None, False
    elif order.status in stopped:
        (done, current), is_stopped = stopped[order.status], True
    else:
        (done, current), is_stopped = reached.get(order.status, (2, 2)), False
    steps = []
    for index, label in enumerate(labels):
        if index < done:
            state = "done"
        elif index == current:
            state = "stopped" if is_stopped else "current"
        else:
            state = "todo"
        steps.append({"label": label, "state": state})
    return steps


def seller_next_step(order):
    """What the seller can do next: ('advance'|'complete', button label), or None."""
    pickup = order.fulfillment_method == "pickup"
    cash = order.payment_method in ("cash_pickup", "cash_delivery")
    labels = {
        "confirmed": ("advance", "Start preparing"),
        "preparing": ("advance", "Mark ready for pickup" if pickup else "Mark ready for delivery"),
        "out_for_delivery": ("advance", "Mark delivered"),
    }
    if order.status == "ready":
        labels["ready"] = ("complete", "Complete pickup" + (" and record cash" if cash else "")) if pickup else ("advance", "Send out for delivery")
    if order.status == "delivered":
        labels["delivered"] = ("complete", "Complete order" + (" and record cash" if cash else ""))
    return labels.get(order.status)
