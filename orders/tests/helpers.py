from orders.models import Order
from orders.services.workflow import advance_order, complete_handoff, handoff_status


def finish_order(actor, order_id):
    """Walk a confirmed order through every seller step until it is completed."""
    order = Order.objects.get(pk=order_id)
    if order.status == Order.Status.COMPLETED:
        return order
    while order.status != handoff_status(order):
        order = advance_order(actor, order_id)
    return complete_handoff(actor, order_id)
