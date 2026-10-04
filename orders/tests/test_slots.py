from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from sellers.models import SellerProfile


class FulfillmentSlotRulesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="slot-seller", password="safe-test-password-2026",
        )
        cls.seller = SellerProfile.objects.create(
            user=user,
            storefront_name="Slot Kitchen",
            status=SellerProfile.Status.APPROVED,
        )

    def test_preorder_deadline_must_precede_fulfillment_start(self):
        from orders.models import FulfillmentSlot

        start = timezone.now() + timedelta(days=2)
        slot = FulfillmentSlot(
            seller=self.seller,
            order_type=FulfillmentSlot.OrderType.PREORDER,
            starts_at=start,
            ends_at=start + timedelta(hours=2),
            preorder_deadline=start + timedelta(minutes=1),
            allows_pickup=True,
            allows_delivery=True,
        )

        with self.assertRaises(ValidationError):
            slot.full_clean()

    def test_slot_window_must_end_after_it_starts(self):
        from orders.models import FulfillmentSlot

        start = timezone.now() + timedelta(days=1)
        slot = FulfillmentSlot(
            seller=self.seller,
            order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start,
            ends_at=start,
            allows_pickup=True,
            allows_delivery=False,
        )

        with self.assertRaises(ValidationError):
            slot.full_clean()

