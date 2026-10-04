from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from fulfillment.models import DeliveryTariff, DemoLocation
from fulfillment.services import calculate_distance_km, pickup_fee, quote_delivery


class LocationPricingTests(TestCase):
    def setUp(self):
        self.origin = DemoLocation.objects.create(
            code="siam", label="Siam", city="Bangkok",
            latitude=Decimal("13.750000"), longitude=Decimal("100.500000"),
        )
        self.destination = DemoLocation.objects.create(
            code="asok", label="Asok", city="Bangkok",
            latitude=Decimal("13.750000"), longitude=Decimal("100.510000"),
        )
        DeliveryTariff.objects.create(version=1)

    def test_distance_is_deterministic_and_zero_for_same_location(self):
        self.assertEqual(calculate_distance_km(self.origin, self.origin), Decimal("0.0000"))
        self.assertEqual(calculate_distance_km(self.origin, self.destination), Decimal("1.0801"))
        self.assertEqual(calculate_distance_km(self.destination, self.origin), Decimal("1.0801"))

    def test_delivery_quote_uses_rounded_simulated_distance_and_fee(self):
        quote = quote_delivery(self.origin, self.destination, Decimal("500.00"))
        self.assertEqual(quote.distance_km, Decimal("1.40"))
        self.assertEqual(quote.fee, Decimal("37.00"))
        self.assertEqual(quote.tariff_version, 1)
        self.assertEqual(quote.label, "Simulated distance and delivery charge")

    def test_pickup_and_same_location_delivery_have_distinct_fees(self):
        self.assertEqual(pickup_fee(), Decimal("0.00"))
        quote = quote_delivery(self.origin, self.origin, Decimal("50.00"))
        self.assertEqual(quote.distance_km, Decimal("0.00"))
        self.assertEqual(quote.fee, Decimal("30.00"))

    def test_latest_active_tariff_is_used_and_version_is_returned(self):
        DeliveryTariff.objects.create(
            version=2, base_fee=Decimal("40.00"),
            per_km_fee=Decimal("6.00"), route_multiplier=Decimal("1.50"),
        )
        quote = quote_delivery(self.origin, self.destination, Decimal("100.00"))
        self.assertEqual(quote.distance_km, Decimal("1.62"))
        self.assertEqual(quote.fee, Decimal("49.72"))
        self.assertEqual(quote.tariff_version, 2)
        DeliveryTariff.objects.filter(version=2).update(is_active=False)
        self.assertEqual(quote_delivery(self.origin, self.destination, Decimal("100.00")).tariff_version, 1)

    def test_inactive_or_outside_bangkok_location_is_rejected(self):
        self.destination.is_active = False
        self.destination.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            quote_delivery(self.origin, self.destination, Decimal("100.00"))
        self.destination.is_active = True
        self.destination.latitude = Decimal("18.788300")
        self.destination.save(update_fields=["is_active", "latitude"])
        with self.assertRaises(ValidationError):
            quote_delivery(self.origin, self.destination, Decimal("100.00"))

    def test_invalid_subtotal_or_missing_active_tariff_is_rejected(self):
        with self.assertRaises(ValidationError):
            quote_delivery(self.origin, self.destination, Decimal("-0.01"))
        DeliveryTariff.objects.update(is_active=False)
        with self.assertRaises(ValidationError):
            quote_delivery(self.origin, self.destination, Decimal("1.00"))


class SeedLocationTests(TestCase):
    def test_seed_is_idempotent_and_keeps_existing_label(self):
        call_command("seed_locations", verbosity=0)
        locations = list(DemoLocation.objects.order_by("code"))
        self.assertGreaterEqual(len(locations), 6)
        self.assertTrue(all(location.city == "Bangkok" and location.is_active for location in locations))
        self.assertTrue(all(location.code and location.label for location in locations))
        locations[0].label = "Custom demo label"
        locations[0].save(update_fields=["label"])
        call_command("seed_locations", verbosity=0)
        self.assertEqual(DemoLocation.objects.count(), len(locations))
        self.assertEqual(DemoLocation.objects.get(pk=locations[0].pk).label, "Custom demo label")
        self.assertEqual(DeliveryTariff.objects.count(), 1)
