from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class DemoBuyer(models.Model):
    """Marks a buyer account created by seed_demo so reruns cannot adopt strangers."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="demo_buyer_identity",
    )


class DemoSlot(models.Model):
    """Identity of the currently usable seeded slot for one seller/order type."""

    seller = models.ForeignKey("sellers.SellerProfile", on_delete=models.PROTECT, related_name="demo_slots")
    order_type = models.CharField(max_length=10, choices=[("standard", "Standard"), ("preorder", "Pre-order")])
    slot = models.OneToOneField("orders.FulfillmentSlot", on_delete=models.PROTECT, related_name="demo_identity")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["seller", "order_type"], name="unique_demo_seller_slot_type"),
        ]

    def clean(self):
        if self.slot_id and (
            self.slot.seller_id != self.seller_id or self.slot.order_type != self.order_type
        ):
            raise ValidationError("Demo slot seller and type must match the linked slot.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
