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
        self.assertContains(self.client.get(reverse("orders:detail", args=[order.pk])), "Order totals")

    def test_another_buyer_cannot_view_order(self):
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        order = checkout(self.buyer, idempotency_key="private-order", payment_method=Order.PaymentMethod.CASH_PICKUP)
        stranger = get_user_model().objects.create_user(username="stranger", password="test-password-2026")
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(reverse("orders:detail", args=[order.pk])).status_code, 404)

    def _second_kitchen(self):
        other = FoodListing.objects.public().exclude(seller=self.listing.seller).first()
        start = timezone.now() + timedelta(hours=1)
        other_slot = FulfillmentSlot.objects.create(seller=other.seller, order_type="standard", starts_at=start, ends_at=start + timedelta(hours=2))
        ListingStock.objects.create(listing=other, slot=other_slot, capacity=3)
        return other, other_slot

    def test_cart_accepts_a_second_kitchen_and_shows_both(self):
        from orders.models import Cart
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:add", args=[self.listing.pk]), {"slot": self.slot.pk, "quantity": 1})
        other, other_slot = self._second_kitchen()
        response = self.client.post(reverse("orders:add", args=[other.pk]), {"slot": other_slot.pk, "quantity": 2})
        self.assertEqual(response.status_code, 302)
        cart = Cart.objects.get(buyer=self.buyer)
        self.assertEqual(cart.items.count(), 2)
        page = self.client.get(reverse("orders:cart"))
        self.assertContains(page, self.listing.seller.storefront_name)
        self.assertContains(page, other.seller.storefront_name)
        self.assertContains(page, "Place 2 orders")

    def test_checkout_places_one_order_per_kitchen(self):
        from orders.models import Order
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:add", args=[self.listing.pk]), {"slot": self.slot.pk, "quantity": 1})
        other, other_slot = self._second_kitchen()
        self.client.post(reverse("orders:add", args=[other.pk]), {"slot": other_slot.pk, "quantity": 2})
        response = self.client.post(reverse("orders:checkout"), {"idempotency_key": "multi-kitchen-1", "payment_method": "cash_pickup"})
        self.assertRedirects(response, reverse("orders:list"))
        orders = list(Order.objects.filter(buyer=self.buyer).order_by("pk"))
        self.assertEqual(len(orders), 2)
        self.assertEqual({o.seller_id for o in orders}, {self.listing.seller_id, other.seller_id})
        self.assertTrue(all(o.status == Order.Status.CASH_DUE for o in orders))
        # a repeated submit does not create more orders
        self.client.post(reverse("orders:checkout"), {"idempotency_key": "multi-kitchen-1", "payment_method": "cash_pickup"})
        self.assertEqual(Order.objects.filter(buyer=self.buyer).count(), 2)

    def test_one_payment_covers_every_kitchen_in_the_cart(self):
        from decimal import Decimal
        from orders.models import Order
        from payments.models import PaymentAttempt
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:add", args=[self.listing.pk]), {"slot": self.slot.pk, "quantity": 1})
        other, other_slot = self._second_kitchen()
        self.client.post(reverse("orders:add", args=[other.pk]), {"slot": other_slot.pk, "quantity": 1})
        response = self.client.post(reverse("orders:checkout"), {"idempotency_key": "multi-kitchen-2", "payment_method": "mock_promptpay"})
        first, second = Order.objects.filter(buyer=self.buyer).order_by("pk")
        self.assertRedirects(response, reverse("payments:pay", args=[first.pk]))
        total = first.customer_total + second.customer_total
        # the second order's address shows the same single payment page
        page = self.client.get(reverse("payments:pay", args=[second.pk]))
        self.assertContains(page, "Payment for your 2 orders")
        self.assertContains(page, f"{total}")
        self.assertContains(page, first.seller.storefront_name)
        self.assertContains(page, second.seller.storefront_name)
        # a wrong total is refused and nothing is paid
        self.client.post(reverse("payments:result", args=[first.pk]), {"outcome": "succeeded", "amount": str(first.customer_total)})
        first.refresh_from_db(); second.refresh_from_db()
        self.assertEqual(first.status, Order.Status.PENDING_PAYMENT)
        self.assertEqual(second.status, Order.Status.PENDING_PAYMENT)
        # one payment pays both kitchens
        self.client.post(reverse("payments:result", args=[first.pk]), {"outcome": "succeeded", "amount": str(total)})
        first.refresh_from_db(); second.refresh_from_db()
        self.assertEqual(first.status, Order.Status.AWAITING_SELLER)
        self.assertEqual(second.status, Order.Status.AWAITING_SELLER)
        attempts = PaymentAttempt.objects.filter(order__in=[first, second])
        self.assertEqual(attempts.count(), 2)
        self.assertTrue(all(a.state == PaymentAttempt.State.SUCCEEDED for a in attempts))
        self.assertEqual({a.order_id: a.amount for a in attempts}, {first.pk: first.customer_total, second.pk: second.customer_total})

    def test_cancelling_a_shared_payment_cancels_every_kitchen_order(self):
        from orders.models import Order
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:add", args=[self.listing.pk]), {"slot": self.slot.pk, "quantity": 1})
        other, other_slot = self._second_kitchen()
        self.client.post(reverse("orders:add", args=[other.pk]), {"slot": other_slot.pk, "quantity": 1})
        self.client.post(reverse("orders:checkout"), {"idempotency_key": "multi-kitchen-3", "payment_method": "mock_card"})
        first, second = Order.objects.filter(buyer=self.buyer).order_by("pk")
        self.client.post(reverse("orders:cancel", args=[first.pk]))
        first.refresh_from_db(); second.refresh_from_db()
        self.assertEqual(first.status, Order.Status.CANCELLED)
        self.assertEqual(second.status, Order.Status.CANCELLED)

    def test_stale_cart_explains_cutoff_and_preserves_items(self):
        from orders.models import Cart
        from orders.services.cart import add_to_cart
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        FulfillmentSlot.objects.filter(pk=self.slot.pk).update(ends_at=timezone.now() + timedelta(minutes=10), starts_at=timezone.now() - timedelta(hours=1))
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("orders:cart"))
        self.assertContains(response, "Ordering closed")
        self.assertContains(response, "Review your cart")
        self.assertEqual(Cart.objects.get(buyer=self.buyer).items.count(), 1)

    def test_price_change_needs_signed_detail_review_not_quantity_update(self):
        from orders.models import Cart
        from orders.services.cart import add_to_cart
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        item = Cart.objects.get(buyer=self.buyer).items.get()
        old_price = item.acknowledged_unit_price
        FoodListing.objects.filter(pk=self.listing.pk).update(price=old_price + 1)
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:update", args=[item.pk]), {"quantity": 1})
        item.refresh_from_db()
        self.assertEqual(item.acknowledged_unit_price, old_price)
        detail = self.client.get(reverse("catalog:detail", args=[self.listing.pk]), {"review_cart_item": item.pk})
        self.assertContains(detail, "Confirm current ingredients and price")
        self.client.post(reverse("orders:acknowledge", args=[item.pk]), {"review_token": detail.context["review_token"]})
        item.refresh_from_db()
        self.assertEqual(item.acknowledged_unit_price, old_price + 1)

    def test_cart_explains_quote_expiry_and_commission_not_extra_customer_charge(self):
        from orders.services.cart import add_to_cart
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        self.client.force_login(self.buyer)
        self.client.post(reverse("orders:quote"), {"method": "pickup"})
        response = self.client.get(reverse("orders:cart"))
        self.assertContains(response, "Customer total")
        self.assertContains(response, "deducted from seller food earnings")
        self.assertContains(response, "is free")

    def test_order_explains_payment_separately_from_fulfillment_and_next_actor(self):
        from orders.services.cart import add_to_cart
        from orders.services.checkout import checkout
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        order = checkout(self.buyer, idempotency_key="status-explanation", payment_method=Order.PaymentMethod.CASH_PICKUP)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("orders:detail", args=[order.pk]))
        self.assertContains(response, "Payment status")
        self.assertContains(response, "Fulfillment status")
        self.assertContains(response, "Cash due at pickup")
        self.assertContains(response, "The seller must confirm")

    def test_review_token_rejects_a_second_price_change(self):
        from orders.models import Cart
        from orders.services.cart import add_to_cart
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        item = Cart.objects.get(buyer=self.buyer).items.get()
        self.client.force_login(self.buyer)
        page = self.client.get(reverse("catalog:detail", args=[self.listing.pk]), {"review_cart_item": item.pk})
        FoodListing.objects.filter(pk=self.listing.pk).update(price=item.acknowledged_unit_price + 2)
        self.client.post(reverse("orders:acknowledge", args=[item.pk]), {"review_token": page.context["review_token"]})
        item.refresh_from_db()
        self.assertEqual(item.acknowledged_unit_price, self.listing.price)

    def test_stale_replacement_confirmation_cannot_clear_changed_cart(self):
        from orders.models import Cart
        from orders.services.cart import add_to_cart
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        cart = Cart.objects.get(buyer=self.buyer)
        stale_revision = cart.revision
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        self.client.force_login(self.buyer)
        response = self.client.post(reverse("orders:add", args=[self.listing.pk]), {
            "slot": self.slot.pk, "quantity": 1, "replace": "yes", "expected_revision": stale_revision,
        })
        self.assertContains(response, "Your cart changed")
        self.assertEqual(cart.items.get().quantity, 2)

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
