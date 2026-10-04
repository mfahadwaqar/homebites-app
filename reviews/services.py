from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from orders.models import Order
from reviews.models import ModerationEvent, Report, Review


@transaction.atomic
def submit_review(order, buyer, *, rating, comment=""):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.buyer_id != buyer.pk or order.status != Order.Status.COMPLETED:
        raise ValidationError("Only the buyer of a completed order can review it.")
    if Review.objects.filter(order=order).exists():
        raise ValidationError("This order has already been reviewed.")
    return Review.objects.create(order=order, rating=rating, comment=comment.strip())


def submit_report(reporter, *, seller=None, listing=None, reason):
    return Report.objects.create(
        reporter=reporter, seller=seller, listing=listing, reason=reason.strip(),
    )


def _require_staff(actor, reason):
    if not actor.is_authenticated or not actor.is_active or not actor.is_staff:
        raise ValidationError("Only active staff can moderate content.")
    if not reason or not reason.strip():
        raise ValidationError("Record a moderation reason.")


@transaction.atomic
def moderate_review(review, actor, *, decision, reason):
    _require_staff(actor, reason)
    if decision not in (Review.Status.APPROVED, Review.Status.HIDDEN):
        raise ValidationError("Choose an approval or hide decision.")
    review = Review.objects.select_for_update().get(pk=review.pk)
    if review.status != Review.Status.PENDING:
        raise ValidationError("This review has already been moderated.")
    review.status = decision
    review.save(update_fields=["status", "updated_at"])
    ModerationEvent.objects.create(
        actor=actor, review=review, action=f"review_{decision}", reason=reason.strip(),
    )
    return review


@transaction.atomic
def resolve_report(report, actor, *, decision, reason):
    _require_staff(actor, reason)
    if decision not in (Report.Status.RESOLVED, Report.Status.DISMISSED):
        raise ValidationError("Choose a resolution or dismissal.")
    report = Report.objects.select_for_update().get(pk=report.pk)
    if report.status != Report.Status.OPEN:
        raise ValidationError("This report has already been handled.")
    report.status = decision
    report.resolution_reason = reason.strip()
    report.resolved_by = actor
    report.resolved_at = timezone.now()
    report.save(update_fields=["status", "resolution_reason", "resolved_by", "resolved_at"])
    ModerationEvent.objects.create(
        actor=actor, report=report, action=f"report_{decision}", reason=reason.strip(),
    )
    return report
