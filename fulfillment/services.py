"""Offline Bangkok distance and delivery price simulation."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt

from django.core.exceptions import ValidationError

from .models import DeliveryTariff, DemoLocation


SIMULATION_LABEL = "Simulated distance and delivery charge"
_EARTH_RADIUS_KM = 6371.0088
_DISTANCE_PRECISION = Decimal("0.0001")
_QUOTE_PRECISION = Decimal("0.01")


@dataclass(frozen=True)
class DeliveryEstimate:
    distance_km: Decimal
    fee: Decimal
    tariff_version: int
    label: str = SIMULATION_LABEL


def _validate_location(location: DemoLocation) -> tuple[float, float]:
    if not isinstance(location, DemoLocation):
        raise ValidationError("Select a supported demo location.")
    if not location.is_active or location.city.strip().casefold() != "bangkok":
        raise ValidationError("Select an active Bangkok demo location.")
    try:
        latitude = Decimal(str(location.latitude))
        longitude = Decimal(str(location.longitude))
    except InvalidOperation as exc:
        raise ValidationError("Invalid demo location coordinates.") from exc
    if (
        not latitude.is_finite() or not longitude.is_finite()
        or not Decimal("13.49") <= latitude <= Decimal("13.96")
        or not Decimal("100.32") <= longitude <= Decimal("100.94")
    ):
        raise ValidationError("Demo location coordinates must be in Bangkok.")
    return float(latitude), float(longitude)


def calculate_distance_km(origin: DemoLocation, destination: DemoLocation) -> Decimal:
    """Straight-line Haversine distance, rounded to 4 decimal places."""
    lat1, lon1 = _validate_location(origin)
    lat2, lon2 = _validate_location(destination)
    latitude_delta = radians(lat2 - lat1)
    longitude_delta = radians(lon2 - lon1)
    arc = sin(latitude_delta / 2) ** 2 + (
        cos(radians(lat1)) * cos(radians(lat2)) * sin(longitude_delta / 2) ** 2
    )
    distance = 2 * _EARTH_RADIUS_KM * asin(sqrt(min(1.0, arc)))
    return Decimal(str(distance)).quantize(_DISTANCE_PRECISION, rounding=ROUND_HALF_UP)


def pickup_fee() -> Decimal:
    return Decimal("0.00")


def quote_delivery(
    origin: DemoLocation, destination: DemoLocation, food_subtotal: Decimal,
) -> DeliveryEstimate:
    """Quote a local simulation; no route, provider or network call is made."""
    try:
        subtotal = Decimal(str(food_subtotal))
    except InvalidOperation as exc:
        raise ValidationError("Food subtotal must be a nonnegative amount.") from exc
    if not subtotal.is_finite() or subtotal < 0:
        raise ValidationError("Food subtotal must be a nonnegative amount.")

    straight_line_km = calculate_distance_km(origin, destination)
    tariff = DeliveryTariff.objects.filter(is_active=True).order_by("-version").first()
    if tariff is None:
        raise ValidationError("No active demo delivery tariff is available.")
    distance_km = (straight_line_km * tariff.route_multiplier).quantize(
        _QUOTE_PRECISION, rounding=ROUND_HALF_UP,
    )
    fee = (tariff.base_fee + tariff.per_km_fee * distance_km).quantize(
        _QUOTE_PRECISION, rounding=ROUND_HALF_UP,
    )
    return DeliveryEstimate(
        distance_km=distance_km,
        fee=fee,
        tariff_version=tariff.version,
    )
