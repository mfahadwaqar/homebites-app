from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from catalog.models import FoodListing
from orders.models import FulfillmentSlot, ListingStock, Order


class AvailabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.at = datetime(2026, 10, 16, 12, tzinfo=ZoneInfo("Asia/Bangkok"))
        cls.listing = FoodListing.objects.public().select_related("seller__user").first()
        cls.slot = FulfillmentSlot.objects.create(
            seller=cls.listing.seller, order_type="standard", starts_at=cls.at,
            ends_at=cls.at + timedelta(hours=2),
        )
        cls.stock = ListingStock.objects.create(listing=cls.listing, slot=cls.slot, capacity=3)

    def test_standard_closes_at_preparation_cutoff_not_window_end(self):
        from orders.availability import booking_cutoff, bookable_stocks, evaluate_offer
        cutoff = self.at + timedelta(minutes=90)
        self.assertEqual(booking_cutoff(self.slot), cutoff)
        self.assertEqual(bookable_stocks(at=cutoff - timedelta(microseconds=1)).count(), 1)
        self.assertEqual(bookable_stocks(at=cutoff).count(), 0)
        self.assertEqual(evaluate_offer(self.listing, at=cutoff).state, "closed")

    def test_stock_is_per_window_and_held_portions_are_unavailable(self):
        from orders.availability import evaluate_offer
        self.stock.held = 1
        self.stock.save()
        result = evaluate_offer(self.listing, at=self.at)
        self.assertTrue(result.orderable)
        self.assertEqual(result.windows[0].remaining, 2)
        self.stock.committed = 2
        self.stock.save()
        self.assertEqual(evaluate_offer(self.listing, at=self.at).state, "sold_out")

    def test_paused_and_unscheduled_states_are_distinct(self):
        from orders.availability import evaluate_offer
        self.slot.is_active = False
        self.slot.save()
        self.assertEqual(evaluate_offer(self.listing, at=self.at).state, "paused")
        self.stock.delete()
        self.assertEqual(evaluate_offer(self.listing, at=self.at).state, "unscheduled")

    def test_preorder_deadline_equality_and_preorder_only(self):
        from orders.availability import evaluate_offer
        self.slot.order_type = "preorder"
        self.slot.starts_at = self.at + timedelta(days=2)
        self.slot.ends_at = self.slot.starts_at + timedelta(hours=2)
        self.slot.preorder_deadline = self.at + timedelta(days=1)
        self.slot.save()
        self.assertEqual(evaluate_offer(self.listing, at=self.at).state, "preorder_only")
        self.assertEqual(evaluate_offer(self.listing, at=self.slot.preorder_deadline).state, "preorder_closed")

    def test_unapproved_seller_and_wrong_seller_stock_cannot_be_booked(self):
        from orders.availability import bookable_stocks, evaluate_offer
        self.listing.seller.status = "suspended"
        self.listing.seller.save()
        self.assertFalse(evaluate_offer(self.listing, at=self.at).orderable)
        self.assertEqual(bookable_stocks(at=self.at).count(), 0)

    def test_inconsistent_stock_from_another_seller_is_excluded(self):
        from orders.availability import bookable_stocks, evaluate_offer
        other = FoodListing.objects.public().exclude(seller=self.listing.seller).first()
        slot = FulfillmentSlot.objects.create(seller=other.seller, order_type="standard", starts_at=self.at, ends_at=self.at + timedelta(hours=2))
        ListingStock.objects.filter(pk=self.stock.pk).update(slot=slot)
        self.assertFalse(evaluate_offer(self.listing, at=self.at).orderable)
        self.assertEqual(bookable_stocks(at=self.at).count(), 0)

    def test_cart_and_checkout_reject_selected_slot_at_cutoff(self):
        from orders.services.cart import CartError, add_to_cart
        from orders.services.checkout import CheckoutConflict, checkout
        buyer = get_user_model().objects.create_user(username="availability-buyer")
        with patch("orders.services.cart.timezone.now", return_value=self.at):
            cart = add_to_cart(buyer, self.listing, self.slot, 1)
        cutoff = self.slot.ends_at - timedelta(minutes=30)
        with patch("orders.services.cart.timezone.now", return_value=cutoff):
            with self.assertRaises(CartError):
                add_to_cart(buyer, self.listing, self.slot, 1)
        with patch("orders.services.checkout.timezone.now", return_value=cutoff):
            with self.assertRaises(CheckoutConflict):
                checkout(buyer, idempotency_key="cutoff", payment_method=Order.PaymentMethod.CASH_PICKUP)
        self.assertEqual(cart.items.count(), 1)

    def test_online_hold_is_capped_at_standard_cutoff(self):
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout
        buyer = get_user_model().objects.create_user(username="cutoff-hold-buyer")
        cutoff = self.slot.ends_at - timedelta(minutes=30)
        at = cutoff - timedelta(minutes=5)
        with patch("orders.services.cart.timezone.now", return_value=at):
            add_to_cart(buyer, self.listing, self.slot, 1)
        with patch("orders.services.checkout.timezone.now", return_value=at):
            order = checkout(buyer, idempotency_key="hold-cutoff", payment_method=Order.PaymentMethod.MOCK_CARD)
        self.assertEqual(order.hold_expires_at, cutoff)
