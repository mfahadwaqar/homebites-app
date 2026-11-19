from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class DemoLocation(models.Model):
    code = models.SlugField(max_length=64, unique=True)
    label = models.CharField(max_length=120)
    city = models.CharField(max_length=80, default="Bangkok")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["label", "code"]

    def __str__(self):
        return self.label


class DeliveryTariff(models.Model):
    version = models.PositiveIntegerField(unique=True, validators=[MinValueValidator(1)])
    base_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("30.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    per_km_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("5.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    route_multiplier = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("1.30"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-version"]

    def __str__(self):
        return f"Delivery tariff v{self.version}"
