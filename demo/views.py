from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from demo.models import DemoSlot
from demo.services import refresh_demo_availability
from orders.availability import booking_cutoff, bookable_stocks, window_problem


def _staff(request):
    if not request.user.is_staff or not request.user.is_active:
        raise PermissionDenied


@login_required
@require_GET
def readiness(request):
    _staff(request)
    at = timezone.now()
    rows = []
    for marker in DemoSlot.objects.select_related("slot", "seller").order_by("seller_id", "order_type"):
        count = marker.slot.stocks.count()
        message = window_problem(marker.slot, at=at) or "Window open; portions depend on each dish's stock."
        if count != 10:
            message = "Incomplete original stock associations. Staff review required; refresh will not adopt food."
        rows.append({"marker": marker, "message": message, "cutoff": booking_cutoff(marker.slot), "stock_count": count})
    return render(request, "demo/readiness.html", {"rows": rows, "marker_count": len(rows), "now": at,
        "orderable_count": bookable_stocks(at=at).values("listing_id").distinct().count()})


@login_required
@require_POST
def refresh(request):
    _staff(request)
    from orders.services.checkout import expire_reservations
    at = timezone.now()
    released = expire_reservations(now=at)
    result = refresh_demo_availability(at=at)
    messages.success(request, f"{result} {released} expired payment holds released.")
    for problem in result.problems:
        messages.warning(request, problem)
    return redirect("demo:readiness")
