from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Order
from orders.services.workflow import WorkflowError, accept_order, complete_handoff, reject_order
from payments.services import PaymentConflict
from sellers.models import SellerProfile


@login_required
def queue(request):
    seller = SellerProfile.objects.filter(user=request.user).first()
    orders = Order.objects.none()
    if seller:
        orders = Order.objects.filter(seller=seller).select_related("buyer", "slot")
    return render(request, "orders/workflow/queue.html", {"seller": seller, "orders": orders})


@login_required
def detail(request, order_id):
    order = get_object_or_404(
        Order.objects.filter(seller__user=request.user).select_related("buyer", "slot", "destination").prefetch_related("items"),
        pk=order_id,
    )
    return render(request, "orders/workflow/detail.html", {"order": order})


def _perform(request, order_id, action, **kwargs):
    if not Order.objects.filter(pk=order_id, seller__user=request.user).exists():
        raise Http404
    try:
        action(request.user, order_id, **kwargs)
    except (WorkflowError, PaymentConflict) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Order updated in this local simulation.")
    return redirect("orders_workflow:detail", order_id=order_id)


@login_required
@require_POST
def accept(request, order_id):
    return _perform(request, order_id, accept_order)


@login_required
@require_POST
def reject(request, order_id):
    return _perform(request, order_id, reject_order, reason=request.POST.get("reason", ""))


@login_required
@require_POST
def handoff(request, order_id):
    return _perform(request, order_id, complete_handoff)
