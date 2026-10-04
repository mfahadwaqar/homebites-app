from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import FulfillmentSlot, ListingStock, Order
from orders.services.cart import add_to_cart
from orders.services.checkout import checkout
from orders.services.workflow import accept_order, complete_handoff


class SellerDashboardStatsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.listing = FoodListing.objects.public().order_by("pk").first()
        start = timezone.now() + timedelta(hours=2)
        cls.slot = FulfillmentSlot.objects.create(
            seller=cls.listing.seller,
            order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start,
            ends_at=start + timedelta(hours=2),
        )
        ListingStock.objects.create(listing=cls.listing, slot=cls.slot, capacity=5)
        cls.buyer = get_user_model().objects.create_user(username="stats-buyer", password="test-password-2026")

    def test_only_completed_orders_count_as_seller_earnings(self):
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        completed = checkout(self.buyer, idempotency_key="stats-one", payment_method=Order.PaymentMethod.CASH_PICKUP)
        accept_order(self.listing.seller.user, completed.pk)
        complete_handoff(self.listing.seller.user, completed.pk)
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        checkout(self.buyer, idempotency_key="stats-two", payment_method=Order.PaymentMethod.CASH_PICKUP)

        self.client.force_login(self.listing.seller.user)
        response = self.client.get(reverse("sellers:dashboard"))
        self.assertEqual(response.context["completed_orders"], 1)
        self.assertEqual(response.context["portions_sold"], 1)
        self.assertEqual(response.context["commission_total"], completed.commission)
        self.assertEqual(response.context["seller_earnings"], completed.seller_food_earnings)
        self.assertEqual(completed.commission, (completed.food_subtotal * Decimal("0.10")).quantize(Decimal("0.01")))
