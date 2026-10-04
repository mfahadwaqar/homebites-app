from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalog.models import FoodListing
from fulfillment.models import DemoLocation


class DeliveryQuoteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from orders.models import FulfillmentSlot, ListingStock

        call_command("seed_catalogue", verbosity=0)
        call_command("seed_locations", verbosity=0)
        cls.listing = FoodListing.objects.public().order_by("pk").first()
        cls.origin = DemoLocation.objects.order_by("pk").first()
        cls.destination = DemoLocation.objects.exclude(pk=cls.origin.pk).order_by("pk").first()
        cls.listing.seller.pickup_location = cls.origin
        cls.listing.seller.save(update_fields=["pickup_location"])
        cls.buyer = get_user_model().objects.create_user(
            username="quote-buyer", password="safe-test-password-2026",
        )
        start = timezone.now() + timedelta(hours=2)
        cls.slot = FulfillmentSlot.objects.create(
            seller=cls.listing.seller,
            order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start,
            ends_at=start + timedelta(hours=2),
            allows_pickup=True,
            allows_delivery=True,
        )
        ListingStock.objects.create(listing=cls.listing, slot=cls.slot, capacity=5)

    def test_delivery_quote_is_stored_for_ten_minutes_and_pickup_is_free(self):
        from orders.models import Cart
        from orders.services.cart import add_to_cart, select_fulfillment
        from orders.services.quotes import create_quote

        cart = add_to_cart(self.buyer, self.listing, self.slot, 1)
        select_fulfillment(self.buyer, Cart.Method.DELIVERY, self.destination)
        quote = create_quote(self.buyer)

        self.assertGreater(quote.fee, Decimal("0.00"))
        self.assertEqual(quote.method, Cart.Method.DELIVERY)
        self.assertEqual(quote.destination, self.destination)
        self.assertAlmostEqual((quote.expires_at - quote.created_at).total_seconds(), 600, delta=2)

        select_fulfillment(self.buyer, Cart.Method.PICKUP)
        pickup_quote = create_quote(self.buyer)
        self.assertEqual(pickup_quote.fee, Decimal("0.00"))
        self.assertIsNone(pickup_quote.destination)
        self.assertNotEqual(quote.cart_revision, pickup_quote.cart_revision)

    def test_cart_change_invalidates_existing_delivery_quote(self):
        from orders.models import Cart
        from orders.services.cart import add_to_cart
        from orders.services.quotes import create_quote, valid_quote_for_cart

        cart = add_to_cart(self.buyer, self.listing, self.slot, 1)
        cart.method = Cart.Method.DELIVERY
        cart.destination = self.destination
        cart.revision += 1
        cart.save()
        quote = create_quote(self.buyer)
        self.assertTrue(valid_quote_for_cart(cart, quote))

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        cart.refresh_from_db()

        self.assertFalse(valid_quote_for_cart(cart, quote))

    def test_new_tariff_invalidates_delivery_quote(self):
        from fulfillment.models import DeliveryTariff
        from orders.models import Cart
        from orders.services.cart import add_to_cart, select_fulfillment
        from orders.services.quotes import create_quote, valid_quote_for_cart

        cart = add_to_cart(self.buyer, self.listing, self.slot, 1)
        select_fulfillment(self.buyer, Cart.Method.DELIVERY, self.destination)
        cart.refresh_from_db()
        quote = create_quote(self.buyer)
        self.assertTrue(valid_quote_for_cart(cart, quote))
        DeliveryTariff.objects.create(version=quote.tariff_version + 1, is_active=True)
        self.assertFalse(valid_quote_for_cart(cart, quote))

