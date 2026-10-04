from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class FulfillmentSlot(models.Model):
    class OrderType(models.TextChoices):
        STANDARD = "standard", "Standard order"
        PREORDER = "preorder", "Pre-order"

    seller = models.ForeignKey("sellers.SellerProfile", on_delete=models.PROTECT, related_name="slots")
    order_type = models.CharField(max_length=10, choices=OrderType.choices)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    preorder_deadline = models.DateTimeField(null=True, blank=True)
    allows_pickup = models.BooleanField(default=True)
    allows_delivery = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["starts_at", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(ends_at__gt=F("starts_at")), name="slot_window_positive"),
        ]

    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError("The fulfillment window must end after it starts.")
        if self.order_type == self.OrderType.PREORDER:
            if not self.preorder_deadline:
                raise ValidationError("A pre-order needs a deadline.")
            if self.starts_at and self.preorder_deadline >= self.starts_at:
                raise ValidationError("The pre-order deadline must precede fulfillment.")
        elif self.preorder_deadline is not None:
            raise ValidationError("Standard slots cannot have a pre-order deadline.")
        if not self.allows_pickup and not self.allows_delivery:
            raise ValidationError("A slot must allow pickup or delivery.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.seller} · {self.get_order_type_display()} · {self.starts_at}"


class ListingStock(models.Model):
    listing = models.ForeignKey("catalog.FoodListing", on_delete=models.PROTECT, related_name="stocks")
    slot = models.ForeignKey(FulfillmentSlot, on_delete=models.PROTECT, related_name="stocks")
    capacity = models.PositiveIntegerField()
    held = models.PositiveIntegerField(default=0)
    committed = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["listing", "slot"], name="unique_listing_slot_stock"),
            models.CheckConstraint(condition=Q(capacity__gte=F("held") + F("committed")), name="stock_capacity_safe"),
        ]

    @property
    def available(self):
        return self.capacity - self.held - self.committed

    def clean(self):
        if self.listing_id and self.slot_id and self.listing.seller_id != self.slot.seller_id:
            raise ValidationError("Stock listing and slot must belong to the same seller.")
        if self.capacity < self.held + self.committed:
            raise ValidationError("Capacity cannot be below held plus committed portions.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Cart(models.Model):
    class Method(models.TextChoices):
        PICKUP = "pickup", "Pickup"
        DELIVERY = "delivery", "Simulated delivery"

    buyer = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    seller = models.ForeignKey("sellers.SellerProfile", on_delete=models.PROTECT, null=True, blank=True)
    slot = models.ForeignKey(FulfillmentSlot, on_delete=models.PROTECT, null=True, blank=True)
    method = models.CharField(max_length=8, choices=Method.choices, default=Method.PICKUP)
    destination = models.ForeignKey("fulfillment.DemoLocation", on_delete=models.PROTECT, null=True, blank=True)
    revision = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.buyer}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    listing = models.ForeignKey("catalog.FoodListing", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    acknowledged_ingredient_version = models.PositiveIntegerField()
    acknowledged_unit_price = models.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "listing"], name="unique_cart_listing"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="cart_item_quantity_positive"),
        ]

    @property
    def line_total(self):
        return self.listing.price * self.quantity


class DeliveryQuote(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="quotes")
    cart_revision = models.PositiveIntegerField()
    method = models.CharField(max_length=8, choices=Cart.Method.choices)
    origin = models.ForeignKey("fulfillment.DemoLocation", on_delete=models.PROTECT, null=True, blank=True, related_name="origin_quotes")
    destination = models.ForeignKey("fulfillment.DemoLocation", on_delete=models.PROTECT, null=True, blank=True)
    food_subtotal = models.DecimalField(max_digits=11, decimal_places=2)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    fee = models.DecimalField(max_digits=9, decimal_places=2)
    tariff_version = models.PositiveIntegerField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending mock payment"
        PAYMENT_FAILED = "payment_failed", "Mock payment failed"
        CASH_DUE = "cash_due", "Cash due"
        AWAITING_SELLER = "awaiting_seller", "Awaiting seller"
        CONFIRMED = "confirmed", "Confirmed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"

    class PaymentMethod(models.TextChoices):
        MOCK_PROMPTPAY = "mock_promptpay", "Mock PromptPay"
        MOCK_CARD = "mock_card", "Mock card"
        CASH_DELIVERY = "cash_delivery", "Cash on delivery"
        CASH_PICKUP = "cash_pickup", "Cash on pickup"

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    seller = models.ForeignKey("sellers.SellerProfile", on_delete=models.PROTECT, related_name="orders")
    slot = models.ForeignKey(FulfillmentSlot, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=Status.choices)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    fulfillment_method = models.CharField(max_length=8, choices=Cart.Method.choices)
    destination = models.ForeignKey("fulfillment.DemoLocation", on_delete=models.PROTECT, null=True, blank=True)
    origin_snapshot = models.CharField(max_length=160, blank=True)
    destination_snapshot = models.CharField(max_length=160, blank=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    tariff_version = models.PositiveIntegerField(null=True, blank=True)
    food_subtotal = models.DecimalField(max_digits=11, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=9, decimal_places=2)
    customer_total = models.DecimalField(max_digits=11, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=4)
    commission = models.DecimalField(max_digits=9, decimal_places=2)
    seller_food_earnings = models.DecimalField(max_digits=11, decimal_places=2)
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["buyer", "idempotency_key"], name="unique_buyer_checkout_key"),
        ]
        ordering = ["-created_at", "-pk"]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    listing = models.ForeignKey("catalog.FoodListing", on_delete=models.PROTECT)
    dish_name_snapshot = models.CharField(max_length=120)
    country_snapshot = models.CharField(max_length=40)
    ingredients_snapshot = models.JSONField(default=list)
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=11, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name="order_item_quantity_positive")]


class InventoryReservation(models.Model):
    class State(models.TextChoices):
        HELD = "held", "Held"
        COMMITTED = "committed", "Committed"
        RELEASED = "released", "Released"

    item = models.OneToOneField(OrderItem, on_delete=models.PROTECT, related_name="reservation")
    stock = models.ForeignKey(ListingStock, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    state = models.CharField(max_length=10, choices=State.choices)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name="reservation_quantity_positive")]


class OrderStatusEvent(models.Model):
    """Timestamped audit entry for the local order simulation."""

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="events")
    previous_status = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    note = models.TextField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at", "pk"]
