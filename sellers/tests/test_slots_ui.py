from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import FulfillmentSlot, ListingStock
from orders.models import Order
from orders.services.cart import add_to_cart
from orders.services.checkout import checkout
from sellers.models import SellerProfile


class SellerSlotManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.listing = FoodListing.objects.public().order_by("pk").first()
        cls.seller = cls.listing.seller
        cls.other_listing = FoodListing.objects.public().exclude(seller=cls.seller).first()
        cls.other_user = get_user_model().objects.create_user(username="pending-slot-seller", password="test-password")
        cls.pending = SellerProfile.objects.create(user=cls.other_user, storefront_name="Pending Kitchen")

    def _slot_data(self, **changes):
        starts_at = timezone.now() + timedelta(hours=4)
        data = {
            "order_type": FulfillmentSlot.OrderType.STANDARD,
            "starts_at": starts_at.strftime("%Y-%m-%dT%H:%M"),
            "ends_at": (starts_at + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "preorder_deadline": "",
            "allows_pickup": "on", "allows_delivery": "on", "is_active": "on",
        }
        data.update(changes)
        return data

    def test_approved_seller_creates_own_standard_slot(self):
        self.client.force_login(self.seller.user)
        response = self.client.post(reverse("sellers:slot_create"), self._slot_data())
        self.assertRedirects(response, reverse("sellers:slots"))
        slot = FulfillmentSlot.objects.get(seller=self.seller)
        self.assertEqual(slot.order_type, FulfillmentSlot.OrderType.STANDARD)
        self.assertIsNone(slot.preorder_deadline)

    def test_preorder_deadline_must_precede_its_window(self):
        starts_at = timezone.now() + timedelta(hours=4)
        self.client.force_login(self.seller.user)
        response = self.client.post(reverse("sellers:slot_create"), self._slot_data(
            order_type=FulfillmentSlot.OrderType.PREORDER,
            starts_at=starts_at.strftime("%Y-%m-%dT%H:%M"),
            preorder_deadline=(starts_at + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "deadline must precede fulfillment")
        self.assertFalse(FulfillmentSlot.objects.filter(seller=self.seller).exists())

    def test_approved_seller_can_schedule_preorder_with_earlier_deadline(self):
        starts_at = timezone.now() + timedelta(hours=4)
        self.client.force_login(self.seller.user)
        response = self.client.post(reverse("sellers:slot_create"), self._slot_data(
            order_type=FulfillmentSlot.OrderType.PREORDER,
            starts_at=starts_at.strftime("%Y-%m-%dT%H:%M"),
            preorder_deadline=(starts_at - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
        ))
        self.assertRedirects(response, reverse("sellers:slots"))
        slot = FulfillmentSlot.objects.get(seller=self.seller)
        self.assertLess(slot.preorder_deadline, slot.starts_at)

    def test_pending_seller_cannot_manage_slots(self):
        self.client.force_login(self.pending.user)
        response = self.client.post(reverse("sellers:slot_create"), self._slot_data())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(FulfillmentSlot.objects.filter(seller=self.pending).exists())

    def test_seller_cannot_edit_another_sellers_slot(self):
        starts_at = timezone.now() + timedelta(hours=4)
        slot = FulfillmentSlot.objects.create(
            seller=self.pending, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=starts_at, ends_at=starts_at + timedelta(hours=2),
        )
        self.client.force_login(self.seller.user)
        response = self.client.post(reverse("sellers:slot_edit", args=[slot.pk]), self._slot_data())
        self.assertEqual(response.status_code, 404)

    def test_existing_order_freezes_slot_terms(self):
        starts_at = timezone.now() + timedelta(hours=4)
        slot = FulfillmentSlot.objects.create(
            seller=self.seller, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=starts_at, ends_at=starts_at + timedelta(hours=2),
        )
        ListingStock.objects.create(listing=self.listing, slot=slot, capacity=2)
        buyer = get_user_model().objects.create_user(username="slot-buyer", password="test-password")
        add_to_cart(buyer, self.listing, slot, 1)
        checkout(buyer, idempotency_key="slot-freeze", payment_method=Order.PaymentMethod.CASH_PICKUP)
        self.client.force_login(self.seller.user)
        response = self.client.post(reverse("sellers:slot_edit", args=[slot.pk]), self._slot_data(
            starts_at=starts_at.strftime("%Y-%m-%dT%H:%M"),
            ends_at=(starts_at + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M"),
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot change its fulfillment terms")
        slot.refresh_from_db()
        self.assertEqual(slot.ends_at, starts_at + timedelta(hours=2))

    def test_stock_capacity_cannot_fall_below_committed_portions(self):
        starts_at = timezone.now() + timedelta(hours=4)
        slot = FulfillmentSlot.objects.create(
            seller=self.seller, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=starts_at, ends_at=starts_at + timedelta(hours=2),
        )
        stock = ListingStock.objects.create(listing=self.listing, slot=slot, capacity=3, committed=2)
        self.client.force_login(self.seller.user)
        response = self.client.post(
            reverse("sellers:stock_set", args=[slot.pk, self.listing.pk]), {"capacity": 1},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Capacity cannot be below held plus committed portions")
        stock.refresh_from_db()
        self.assertEqual(stock.capacity, 3)

    def test_seller_can_set_capacity_for_own_listing_and_slot(self):
        starts_at = timezone.now() + timedelta(hours=4)
        slot = FulfillmentSlot.objects.create(
            seller=self.seller, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=starts_at, ends_at=starts_at + timedelta(hours=2),
        )
        self.client.force_login(self.seller.user)
        response = self.client.post(
            reverse("sellers:stock_set", args=[slot.pk, self.listing.pk]), {"capacity": 7},
        )
        self.assertRedirects(response, reverse("sellers:slots"))
        stock = ListingStock.objects.get(slot=slot, listing=self.listing)
        self.assertEqual(stock.capacity, 7)
        self.assertEqual(stock.available, 7)

    def test_stock_route_rejects_another_sellers_listing(self):
        starts_at = timezone.now() + timedelta(hours=4)
        slot = FulfillmentSlot.objects.create(
            seller=self.seller, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=starts_at, ends_at=starts_at + timedelta(hours=2),
        )
        self.client.force_login(self.seller.user)
        response = self.client.post(
            reverse("sellers:stock_set", args=[slot.pk, self.other_listing.pk]), {"capacity": 5},
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ListingStock.objects.filter(slot=slot, listing=self.other_listing).exists())
