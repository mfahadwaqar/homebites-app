from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalog.models import FoodListing
from fulfillment.models import DemoLocation


class CheckoutServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from orders.models import FulfillmentSlot, ListingStock

        call_command("seed_catalogue", verbosity=0)
        call_command("seed_locations", verbosity=0)
        cls.buyer = get_user_model().objects.create_user(
            username="checkout-buyer", password="safe-test-password-2026",
        )
        cls.listing = FoodListing.objects.public().order_by("pk").first()
        cls.listing.seller.pickup_location = DemoLocation.objects.order_by("pk").first()
        cls.listing.seller.save(update_fields=["pickup_location"])
        start = timezone.now() + timedelta(hours=2)
        cls.slot = FulfillmentSlot.objects.create(
            seller=cls.listing.seller,
            order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start,
            ends_at=start + timedelta(hours=2),
            allows_pickup=True,
            allows_delivery=True,
        )
        ListingStock.objects.create(
            listing=cls.listing, slot=cls.slot, capacity=1,
        )

    def test_repeated_cash_checkout_creates_one_order_and_one_stock_commit(self):
        from orders.models import ListingStock, Order
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        first = checkout(
            self.buyer,
            idempotency_key="cash-checkout-one",
            payment_method=Order.PaymentMethod.CASH_PICKUP,
        )
        second = checkout(
            self.buyer,
            idempotency_key="cash-checkout-one",
            payment_method=Order.PaymentMethod.CASH_PICKUP,
        )

        stock = ListingStock.objects.get(listing=self.listing, slot=self.slot)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(stock.committed, 1)
        self.assertEqual(stock.held, 0)
        self.assertEqual(first.items.get().ingredients_snapshot, self.listing.ingredients)
        self.assertEqual(list(first.events.values_list("status", flat=True)), [Order.Status.CASH_DUE])

    def test_changed_ingredients_require_reconfirmation_before_order(self):
        from orders.models import Order
        from orders.services.cart import add_to_cart
        from orders.services.checkout import CheckoutConflict, checkout

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        self.listing.ingredients = ["a revised recipe ingredient"]
        self.listing.save()

        with self.assertRaises(CheckoutConflict):
            checkout(
                self.buyer,
                idempotency_key="stale-ingredients-one",
                payment_method=Order.PaymentMethod.CASH_PICKUP,
            )

        self.assertEqual(Order.objects.count(), 0)

    def test_expired_online_hold_releases_stock_once(self):
        from orders.models import ListingStock, Order
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout, expire_reservations

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        order = checkout(
            self.buyer,
            idempotency_key="online-checkout-one",
            payment_method=Order.PaymentMethod.MOCK_PROMPTPAY,
        )
        stock = ListingStock.objects.get(listing=self.listing, slot=self.slot)
        stock.refresh_from_db()
        self.assertEqual(stock.held, 1)
        self.assertEqual(stock.committed, 0)

        expire_reservations(now=order.hold_expires_at + timedelta(seconds=1))
        expire_reservations(now=order.hold_expires_at + timedelta(seconds=2))

        stock.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(stock.held, 0)
        self.assertEqual(order.status, Order.Status.EXPIRED)
        self.assertEqual(list(order.events.values_list("status", flat=True)), [
            Order.Status.PENDING_PAYMENT, Order.Status.EXPIRED,
        ])

    def test_pickup_origin_snapshot_survives_seller_location_change(self):
        from orders.models import Order
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout

        origin = self.listing.seller.pickup_location
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        order = checkout(
            self.buyer, idempotency_key="origin-snapshot",
            payment_method=Order.PaymentMethod.CASH_PICKUP,
        )
        self.listing.seller.pickup_location = DemoLocation.objects.exclude(pk=origin.pk).order_by("pk").first()
        self.listing.seller.save(update_fields=["pickup_location"])
        order.refresh_from_db()
        self.assertEqual(order.origin_snapshot, origin.label)

    def test_expiry_command_releases_overdue_mock_hold(self):
        from orders.models import ListingStock, Order
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        order = checkout(
            self.buyer, idempotency_key="command-expire", payment_method=Order.PaymentMethod.MOCK_CARD,
        )
        order.hold_expires_at = timezone.now() - timedelta(seconds=1)
        order.save(update_fields=["hold_expires_at"])
        call_command("expire_demo_holds", verbosity=0)
        order.refresh_from_db()
        stock = ListingStock.objects.get(listing=self.listing, slot=self.slot)
        self.assertEqual(order.status, Order.Status.EXPIRED)
        self.assertEqual(stock.held, 0)

    def test_buyer_cannot_cancel_after_seller_confirmation(self):
        from orders.models import ListingStock, Order
        from orders.services.cart import add_to_cart
        from orders.services.checkout import CheckoutConflict, cancel_order, checkout
        from orders.services.workflow import accept_order

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        order = checkout(
            self.buyer, idempotency_key="confirmed-no-buyer-cancel",
            payment_method=Order.PaymentMethod.CASH_PICKUP,
        )
        accept_order(self.listing.seller.user, order.pk)
        with self.assertRaises(CheckoutConflict):
            cancel_order(self.buyer, order)
        order.refresh_from_db()
        stock = ListingStock.objects.get(listing=self.listing, slot=self.slot)
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(stock.committed, 1)

    def test_buyer_can_cancel_open_mock_attempt_without_fake_refund(self):
        from orders.models import ListingStock, Order
        from orders.services.cart import add_to_cart
        from orders.services.checkout import cancel_order, checkout
        from payments.models import PaymentAttempt
        from payments.services import create_payment_attempt

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        order = checkout(
            self.buyer, idempotency_key="cancel-open-attempt",
            payment_method=Order.PaymentMethod.MOCK_PROMPTPAY,
        )
        attempt = create_payment_attempt(self.buyer, order, idempotency_key="open-attempt")
        cancel_order(self.buyer, order)
        order.refresh_from_db()
        attempt.refresh_from_db()
        stock = ListingStock.objects.get(listing=self.listing, slot=self.slot)
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(attempt.state, PaymentAttempt.State.CANCELLED)
        self.assertEqual(stock.held, 0)

