from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import FulfillmentSlot, ListingStock, Order
from orders.services.cart import add_to_cart
from orders.services.checkout import CheckoutConflict, checkout


class LastPortionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        call_command("seed_catalogue", verbosity=0)
        self.listing = FoodListing.objects.public().order_by("pk").first()
        start = timezone.now() + timedelta(hours=2)
        self.slot = FulfillmentSlot.objects.create(
            seller=self.listing.seller,
            order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start,
            ends_at=start + timedelta(hours=2),
        )
        self.stock = ListingStock.objects.create(listing=self.listing, slot=self.slot, capacity=1)
        self.buyers = [
            get_user_model().objects.create_user(username=f"racing-buyer-{index}", password="test-password-2026")
            for index in range(2)
        ]
        for buyer in self.buyers:
            add_to_cart(buyer, self.listing, self.slot, 1)

    def test_two_buyers_cannot_commit_the_same_last_portion(self):
        barrier = Barrier(2)

        def run_checkout(buyer):
            close_old_connections()
            barrier.wait(timeout=5)
            try:
                checkout(
                    buyer,
                    idempotency_key=f"race-{buyer.pk}",
                    payment_method=Order.PaymentMethod.CASH_PICKUP,
                )
                return "created"
            except CheckoutConflict:
                return "sold_out"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run_checkout, self.buyers))
        self.stock.refresh_from_db()
        self.assertCountEqual(results, ["created", "sold_out"])
        self.assertEqual(self.stock.committed, 1)
        self.assertEqual(self.stock.available, 0)
        self.assertEqual(Order.objects.count(), 1)
