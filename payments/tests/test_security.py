from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import FulfillmentSlot, InventoryReservation, ListingStock, Order, OrderItem


class PaymentEndpointSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.listing = FoodListing.objects.public().first()
        cls.buyer = get_user_model().objects.create_user(username="csrf-payment-buyer", password="demo-pass")
        cls.other = get_user_model().objects.create_user(username="csrf-payment-other", password="demo-pass")
        start = timezone.now() + timedelta(hours=2)
        cls.slot = FulfillmentSlot.objects.create(
            seller=cls.listing.seller, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start, ends_at=start + timedelta(hours=1),
        )
        cls.stock = ListingStock.objects.create(listing=cls.listing, slot=cls.slot, capacity=1, held=1)
        cls.order = Order.objects.create(
            buyer=cls.buyer, seller=cls.listing.seller, slot=cls.slot,
            idempotency_key="csrf-payment-order", status=Order.Status.PENDING_PAYMENT,
            payment_method=Order.PaymentMethod.MOCK_CARD, fulfillment_method="pickup",
            food_subtotal=Decimal("100.00"), delivery_fee=Decimal("0.00"),
            customer_total=Decimal("100.00"), commission_rate=Decimal("0.1000"),
            commission=Decimal("10.00"), seller_food_earnings=Decimal("90.00"),
            hold_expires_at=timezone.now() + timedelta(minutes=15),
        )
        item = OrderItem.objects.create(
            order=cls.order, listing=cls.listing, dish_name_snapshot=cls.listing.dish.name,
            country_snapshot=cls.listing.dish.country.name, ingredients_snapshot=cls.listing.ingredients,
            unit_price=Decimal("100.00"), quantity=1, line_total=Decimal("100.00"),
        )
        InventoryReservation.objects.create(
            item=item, stock=cls.stock, quantity=1, state=InventoryReservation.State.HELD,
            expires_at=cls.order.hold_expires_at,
        )

    def test_mock_result_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.buyer)
        payment_url = reverse("payments:pay", args=[self.order.pk])
        result_url = reverse("payments:result", args=[self.order.pk])
        self.assertEqual(client.get(payment_url).status_code, 200)

        denied = client.post(result_url, {"outcome": "succeeded", "amount": "100.00"})
        self.assertEqual(denied.status_code, 403)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_PAYMENT)

        token = client.cookies["csrftoken"].value
        accepted = client.post(
            result_url, {"outcome": "succeeded", "amount": "100.00", "csrfmiddlewaretoken": token},
        )
        self.assertEqual(accepted.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.AWAITING_SELLER)

    def test_other_buyer_cannot_submit_result_even_with_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.other)
        client.get(reverse("accounts:profile"))
        token = client.cookies.get("csrftoken")
        if token is None:
            from django.middleware.csrf import get_token
            from django.test import RequestFactory

            request = RequestFactory().get("/")
            csrf_token = get_token(request)
            client.cookies["csrftoken"] = request.META["CSRF_COOKIE"]
        else:
            csrf_token = token.value
        response = client.post(
            reverse("payments:result", args=[self.order.pk]),
            {"outcome": "succeeded", "amount": "100.00", "csrfmiddlewaretoken": csrf_token},
        )
        self.assertEqual(response.status_code, 404)
