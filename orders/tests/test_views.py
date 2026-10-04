from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import FoodListing
from fulfillment.models import DemoLocation
from orders.models import FulfillmentSlot, ListingStock, Order


class BuyerJourneyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        call_command("seed_locations", verbosity=0)
        cls.listing = FoodListing.objects.public().order_by("pk").first()
        cls.buyer = get_user_model().objects.create_user(
            username="journey-buyer", password="journey-test-password-2026",
        )
        cls.listing.seller.pickup_location = DemoLocation.objects.order_by("pk").first()
        cls.listing.seller.save(update_fields=["pickup_location"])
        start = timezone.now() + timedelta(hours=2)
        cls.slot = FulfillmentSlot.objects.create(
            seller=cls.listing.seller,
            order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start,
            ends_at=start + timedelta(hours=2),
        )
        ListingStock.objects.create(listing=cls.listing, slot=cls.slot, capacity=4)

    def test_buyer_can_add_pickup_checkout_and_read_own_order(self):
        self.client.force_login(self.buyer)
        add = self.client.post(reverse("orders:add", args=[self.listing.pk]), {
            "slot": self.slot.pk, "quantity": 2,
        })
        self.assertRedirects(add, reverse("orders:cart"))
        cart_page = self.client.get(reverse("orders:cart"))
        self.assertContains(cart_page, self.listing.dish.name)
        self.assertContains(cart_page, self.listing.ingredients[0])
        self.assertContains(cart_page, "Pickup")

        result = self.client.post(reverse("orders:checkout"), {
            "payment_method": Order.PaymentMethod.CASH_PICKUP,
            "idempotency_key": "buyer-journey-one",
        })
        order = Order.objects.get(buyer=self.buyer)
        self.assertRedirects(result, reverse("orders:detail", args=[order.pk]))
        self.assertEqual(order.status, Order.Status.CASH_DUE)
        self.assertContains(self.client.get(reverse("orders:detail", args=[order.pk])), "Simulated")

    def test_another_buyer_cannot_view_order(self):
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        order = checkout(self.buyer, idempotency_key="private-order", payment_method=Order.PaymentMethod.CASH_PICKUP)
        stranger = get_user_model().objects.create_user(username="stranger", password="test-password-2026")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(reverse("orders:detail", args=[order.pk])).status_code, 404)

    def test_failed_payment_order_hides_cancel_action(self):
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        order = checkout(self.buyer, idempotency_key="failed-no-cancel", payment_method=Order.PaymentMethod.MOCK_CARD)
        order.status = Order.Status.PAYMENT_FAILED
        order.save(update_fields=["status"])
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("orders:detail", args=[order.pk]))
        self.assertNotContains(response, "Cancel order")

    def test_new_cart_add_reclaims_an_overdue_payment_hold(self):
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout

        add_to_cart(self.buyer, self.listing, self.slot, 4)
        order = checkout(self.buyer, idempotency_key="view-expire", payment_method=Order.PaymentMethod.MOCK_CARD)
        order.hold_expires_at = timezone.now() - timedelta(seconds=1)
        order.save(update_fields=["hold_expires_at"])
        another = get_user_model().objects.create_user(username="late-buyer", password="test-password-2026")
        self.client.force_login(another)
        response = self.client.post(reverse("orders:add", args=[self.listing.pk]), {
            "slot": self.slot.pk, "quantity": 1,
        })
        self.assertRedirects(response, reverse("orders:cart"))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.EXPIRED)
