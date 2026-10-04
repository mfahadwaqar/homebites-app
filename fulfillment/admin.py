from django.contrib import admin

from .models import DeliveryTariff, DemoLocation


@admin.register(DemoLocation)
class DemoLocationAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "city", "latitude", "longitude", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("code", "label")


@admin.register(DeliveryTariff)
class DeliveryTariffAdmin(admin.ModelAdmin):
    list_display = ("version", "base_fee", "per_km_fee", "route_multiplier", "is_active")
    list_filter = ("is_active",)
