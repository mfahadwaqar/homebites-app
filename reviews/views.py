from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Avg, Count
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import FoodListing
from orders.models import Order
from reviews.forms import ReportDecisionForm, ReportForm, ReviewDecisionForm, ReviewForm
from reviews.models import Report, Review
from reviews.services import moderate_review, resolve_report, submit_report, submit_review
from sellers.models import SellerProfile


@login_required
def new_review(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("seller"),
        pk=order_id, buyer=request.user, status=Order.Status.COMPLETED, review__isnull=True,
    )
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            submit_review(order, request.user, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            return redirect("reviews:seller_reviews", seller_id=order.seller_id)
    return render(request, "reviews/new_review.html", {"order": order, "form": form})


def seller_reviews(request, seller_id):
    seller = get_object_or_404(
        SellerProfile.objects.select_related("user"),
        pk=seller_id, status=SellerProfile.Status.APPROVED, user__is_active=True,
    )
    reviews = Review.objects.public().filter(order__seller=seller).select_related("order__buyer")
    summary = reviews.aggregate(count=Count("pk"), average=Avg("rating"))
    return render(request, "reviews/seller_reviews.html", {
        "seller": seller, "reviews": reviews, "summary": summary,
    })


def _report_form(request, *, seller=None, listing=None):
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        report = submit_report(request.user, seller=seller, listing=listing, **form.cleaned_data)
        return redirect("reviews:report_received", report_id=report.pk)
    return render(request, "reviews/report_form.html", {
        "form": form, "seller": seller, "listing": listing,
    })


@login_required
def report_seller(request, seller_id):
    seller = get_object_or_404(
        SellerProfile.objects.select_related("user"),
        pk=seller_id, status=SellerProfile.Status.APPROVED, user__is_active=True,
    )
    return _report_form(request, seller=seller)


@login_required
def report_listing(request, listing_id):
    listing = get_object_or_404(
        FoodListing.objects.public().select_related("dish", "seller"), pk=listing_id,
    )
    return _report_form(request, listing=listing)


@login_required
def report_received(request, report_id):
    report = get_object_or_404(Report, pk=report_id, reporter=request.user)
    return render(request, "reviews/report_received.html", {"report": report})


def _require_staff(request):
    if not request.user.is_staff or not request.user.is_active:
        raise PermissionDenied


@login_required
def moderation_queue(request):
    _require_staff(request)
    return render(request, "reviews/moderation_queue.html", {
        "pending_reviews": Review.objects.filter(status=Review.Status.PENDING).select_related("order__seller", "order__buyer"),
        "open_reports": Report.objects.filter(status=Report.Status.OPEN).select_related("seller", "listing__dish", "reporter"),
        "review_form": ReviewDecisionForm(),
        "report_form": ReportDecisionForm(),
    })


@login_required
@require_POST
def moderate_review_view(request, pk):
    _require_staff(request)
    review = get_object_or_404(Review, pk=pk, status=Review.Status.PENDING)
    form = ReviewDecisionForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Choose a decision and give a reason.")
    try:
        moderate_review(review, request.user, **form.cleaned_data)
    except ValidationError as exc:
        return HttpResponseBadRequest(str(exc))
    return redirect("reviews:moderation_queue")


@login_required
@require_POST
def resolve_report_view(request, pk):
    _require_staff(request)
    report = get_object_or_404(Report, pk=pk, status=Report.Status.OPEN)
    form = ReportDecisionForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest("Choose a decision and give a reason.")
    try:
        resolve_report(report, request.user, **form.cleaned_data)
    except ValidationError as exc:
        return HttpResponseBadRequest(str(exc))
    return redirect("reviews:moderation_queue")
