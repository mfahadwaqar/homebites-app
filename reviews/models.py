from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from orders.models import Order


class ReviewQuerySet(models.QuerySet):
    def public(self):
        return self.filter(status=Review.Status.APPROVED)


class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending moderation"
        APPROVED = "approved", "Approved"
        HIDDEN = "hidden", "Hidden"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="review")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="review_rating_one_to_five"),
        ]

    def clean(self):
        if self.rating is None or not 1 <= self.rating <= 5:
            raise ValidationError({"rating": "Choose a rating from 1 to 5."})
        if self.order_id and self.order.status != Order.Status.COMPLETED:
            raise ValidationError("Only completed orders can be reviewed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Review for order {self.order_id}"


class Report(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="content_reports")
    seller = models.ForeignKey("sellers.SellerProfile", on_delete=models.PROTECT, null=True, blank=True, related_name="reports")
    listing = models.ForeignKey("catalog.FoodListing", on_delete=models.PROTECT, null=True, blank=True, related_name="reports")
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    resolution_reason = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="resolved_content_reports",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(seller__isnull=False, listing__isnull=True) | Q(seller__isnull=True, listing__isnull=False)),
                name="report_exactly_one_target",
            ),
        ]

    def clean(self):
        if bool(self.seller_id) == bool(self.listing_id):
            raise ValidationError("Choose one seller or listing to report.")
        if not self.reason or not self.reason.strip():
            raise ValidationError({"reason": "Explain the concern."})
        if self.status != self.Status.OPEN and (
            not self.resolution_reason.strip() or not self.resolved_by_id or not self.resolved_at
        ):
            raise ValidationError("A report resolution needs staff, time and reason.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Report {self.pk or 'new'}"


class ModerationEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="content_moderation_events")
    review = models.ForeignKey(Review, on_delete=models.PROTECT, null=True, blank=True, related_name="moderation_events")
    report = models.ForeignKey(Report, on_delete=models.PROTECT, null=True, blank=True, related_name="moderation_events")
    action = models.CharField(max_length=30)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(review__isnull=False, report__isnull=True) | Q(review__isnull=True, report__isnull=False)),
                name="moderation_event_one_target",
            ),
        ]

    def clean(self):
        if bool(self.review_id) == bool(self.report_id):
            raise ValidationError("A moderation event needs one target.")
        if not self.reason or not self.reason.strip():
            raise ValidationError({"reason": "Record a moderation reason."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
