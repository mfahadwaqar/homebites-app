from django.conf import settings
from django.db import models


class SellerProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SUSPENDED = "suspended", "Suspended"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_profile")
    storefront_name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    pickup_location = models.ForeignKey(
        "fulfillment.DemoLocation", on_delete=models.PROTECT, null=True, blank=True,
        related_name="seller_pickups",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def can_sell(self):
        return self.status == self.Status.APPROVED and self.user.is_active

    def __str__(self):
        return self.storefront_name
