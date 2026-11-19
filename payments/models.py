from django.db import models
from django.db.models import Q


class PaymentAttempt(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Payment pending"
        SUCCEEDED = "succeeded", "Payment received"
        FAILED = "failed", "Payment failed"
        CANCELLED = "cancelled", "Payment cancelled"
        CASH_DUE = "cash_due", "Cash due"
        CASH_COLLECTED = "cash_collected", "Cash collected"
        SIMULATED_REFUNDED = "simulated_refunded", "Refunded"

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payment_attempts")
    method = models.CharField(max_length=20, choices=[
        ("mock_promptpay", "PromptPay"),
        ("mock_card", "Card"),
        ("cash_delivery", "Cash on delivery"),
        ("cash_pickup", "Cash on pickup"),
    ])
    amount = models.DecimalField(max_digits=11, decimal_places=2)
    idempotency_key = models.CharField(max_length=80)
    mock_reference = models.CharField(max_length=40, unique=True, null=True, blank=True)
    state = models.CharField(max_length=20, choices=State.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["order", "idempotency_key"], name="unique_order_payment_key"),
            models.CheckConstraint(condition=Q(amount__gte=0), name="payment_attempt_nonnegative_amount"),
        ]

    def __str__(self):
        return f"Demo payment {self.pk} for order {self.order_id}"
