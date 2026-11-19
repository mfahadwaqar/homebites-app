from datetime import timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from demo.models import DemoSlot
from orders.models import FulfillmentSlot, ListingStock


class RefreshTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_two_week_absence_rotates_only_marked_slots_and_preserves_old_stock(self):
        from demo.services import refresh_demo_availability
        at = timezone.now() + timedelta(days=14)
        old = set(DemoSlot.objects.values_list("slot_id", flat=True))
        summary = refresh_demo_availability(at=at)
        self.assertEqual(summary.created, 10)
        self.assertFalse(old.intersection(DemoSlot.objects.values_list("slot_id", flat=True)))
        self.assertEqual(ListingStock.objects.filter(slot_id__in=old).count(), 100)
        self.assertEqual(FulfillmentSlot.objects.filter(pk__in=old, is_active=True).count(), 0)
        self.assertEqual(refresh_demo_availability(at=at).created, 0)
        self.assertEqual(ListingStock.objects.count(), 200)
        standard = DemoSlot.objects.filter(order_type="standard").first().slot
        self.assertEqual(standard.starts_at, at + timedelta(minutes=30))
        self.assertEqual(standard.ends_at, at + timedelta(minutes=150))

    def test_pause_and_sold_out_are_not_reset(self):
        from demo.services import refresh_demo_availability
        marker = DemoSlot.objects.first()
        marker.slot.is_active = False
        marker.slot.save()
        stock = ListingStock.objects.exclude(slot=marker.slot).first()
        stock.committed = stock.capacity
        stock.save()
        old_ids = set(DemoSlot.objects.values_list("slot_id", flat=True))
        summary = refresh_demo_availability(at=timezone.now())
        self.assertEqual(summary.paused, 1)
        self.assertEqual(summary.created, 0)
        self.assertEqual(old_ids, set(DemoSlot.objects.values_list("slot_id", flat=True)))
        stock.refresh_from_db()
        self.assertEqual(stock.available, 0)

    def test_missing_associations_report_problem_without_adopting_listings(self):
        from demo.services import refresh_demo_availability
        marker = DemoSlot.objects.first()
        ListingStock.objects.filter(slot=marker.slot).first().delete()
        summary = refresh_demo_availability(at=timezone.now() + timedelta(days=14))
        self.assertTrue(summary.problems)
        marker.refresh_from_db()
        self.assertEqual(marker.slot.stocks.count(), 9)

    def test_preorder_schedule_uses_bangkok_calendar_and_explicit_deadline(self):
        from demo.services import demo_slot_times
        at = timezone.localtime(timezone.now()).replace(hour=23, minute=59)
        start, end, cutoff = demo_slot_times("preorder", at)
        self.assertEqual(timezone.localtime(start).date(), timezone.localdate(at) + timedelta(days=2))
        self.assertEqual(timezone.localtime(start).hour, 18)
        self.assertEqual(end - start, timedelta(hours=2))
        self.assertEqual(start - cutoff, timedelta(days=1))

    def test_refresh_preserves_confirmed_order_history_and_can_finish_old_handoff(self):
        from django.contrib.auth import get_user_model
        from demo.services import refresh_demo_availability
        from orders.models import Order
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout
        from orders.services.workflow import accept_order, complete_handoff
        marker = DemoSlot.objects.filter(order_type="standard").first()
        stock = marker.slot.stocks.select_related("listing__seller__user").first()
        buyer = get_user_model().objects.create_user(username="historical-demo-buyer")
        add_to_cart(buyer, stock.listing, marker.slot, 1)
        order = checkout(buyer, idempotency_key="historical-refresh", payment_method="cash_pickup")
        accept_order(stock.listing.seller.user, order.pk)
        old_slot = order.slot_id
        old_ingredients = order.items.get().ingredients_snapshot
        refresh_demo_availability(at=timezone.now() + timedelta(days=14))
        order.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.slot_id, old_slot)
        self.assertEqual(order.items.get().ingredients_snapshot, old_ingredients)
        self.assertEqual(stock.committed, 1)
        from orders.tests.helpers import finish_order
        finish_order(stock.listing.seller.user, order.pk)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.COMPLETED)


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections
from django.test import TransactionTestCase


class RefreshConcurrencyTests(TransactionTestCase):
    def test_two_refreshes_create_one_replacement_per_marker(self):
        from demo.services import refresh_demo_availability
        call_command("seed_demo", verbosity=0)
        at = timezone.now() + timedelta(days=14)
        barrier = Barrier(2)

        def refresh(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return refresh_demo_availability(at=at).created
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(refresh, range(2)))
        self.assertCountEqual(results, [10, 0])
        self.assertEqual(DemoSlot.objects.count(), 10)
        self.assertEqual(ListingStock.objects.count(), 200)
