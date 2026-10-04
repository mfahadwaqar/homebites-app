from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import include, path, reverse
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import Cart, FulfillmentSlot, InventoryReservation, ListingStock, Order
from orders.services.cart import add_to_cart, select_fulfillment
from orders.services.checkout import checkout
from orders.services.quotes import create_quote
from fulfillment.models import DemoLocation
from accounts.views import HomeBitesLoginView


urlpatterns = [
    path("seller/orders/", include("orders.workflow_urls")),
    path("food/", include("catalog.public_urls")),
    path("sellers/", include("sellers.urls")),
    path("orders/", include("orders.urls")),
    path("payments/", include("payments.urls")),
    path("reviews/", include("reviews.urls")),
    path("account/", include("accounts.urls")),
    path("accounts/login/", HomeBitesLoginView.as_view(), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
]


@override_settings(ROOT_URLCONF="orders.tests.test_workflow")
class SellerWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.listing = FoodListing.objects.public().order_by("pk").first()
        cls.owner = cls.listing.seller.user
        cls.buyer = get_user_model().objects.create_user(username="workflow-buyer", password="test-password")
        cls.outsider = get_user_model().objects.create_user(username="workflow-outsider", password="test-password")
        now = timezone.now()
        cls.slot = FulfillmentSlot.objects.create(
            seller=cls.listing.seller, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=now - timedelta(minutes=5), ends_at=now + timedelta(hours=2),
            allows_pickup=True, allows_delivery=True,
        )
        cls.stock = ListingStock.objects.create(listing=cls.listing, slot=cls.slot, capacity=2)

    def setUp(self):
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        self.order = checkout(
            self.buyer, idempotency_key="workflow-cash-pickup",
            payment_method=Order.PaymentMethod.CASH_PICKUP,
        )

    def test_another_user_cannot_accept_or_reject_seller_order(self):
        from orders.services.workflow import WorkflowError, accept_order, reject_order

        with self.assertRaises(WorkflowError):
            accept_order(self.outsider, self.order.pk)
        with self.assertRaises(WorkflowError):
            reject_order(self.outsider, self.order.pk, reason="Cannot prepare")
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CASH_DUE)

    def test_seller_accepts_then_simulates_pickup_handoff_once(self):
        from orders.services.workflow import accept_order, complete_handoff

        item = self.order.items.get()
        original = (item.dish_name_snapshot, list(item.ingredients_snapshot), item.unit_price)
        accepted = accept_order(self.owner, self.order.pk)
        self.assertEqual(accepted.status, Order.Status.CONFIRMED)
        self.assertEqual(accept_order(self.owner, self.order.pk).status, Order.Status.CONFIRMED)
        completed = complete_handoff(self.owner, self.order.pk)
        self.assertEqual(completed.status, Order.Status.COMPLETED)
        self.assertEqual(complete_handoff(self.owner, self.order.pk).status, Order.Status.COMPLETED)
        item.refresh_from_db()
        self.assertEqual((item.dish_name_snapshot, item.ingredients_snapshot, item.unit_price), original)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.committed, 1)
        events = list(self.order.events.filter(status__in=[Order.Status.CONFIRMED, Order.Status.COMPLETED]).order_by("pk"))
        self.assertEqual([event.status for event in events], [Order.Status.CONFIRMED, Order.Status.COMPLETED])
        self.assertTrue(all(event.occurred_at for event in events))
        self.assertIn("pickup", events[-1].note.lower())

    def test_handoff_before_confirmation_is_rejected(self):
        from orders.services.workflow import WorkflowError, complete_handoff

        with self.assertRaises(WorkflowError):
            complete_handoff(self.owner, self.order.pk)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CASH_DUE)

    def test_reject_releases_committed_stock_once(self):
        from orders.services.workflow import reject_order

        rejected = reject_order(self.owner, self.order.pk, reason="Cannot prepare this dish")
        self.assertEqual(rejected.status, Order.Status.REJECTED)
        self.assertEqual(reject_order(self.owner, self.order.pk, reason="Cannot prepare this dish").status, Order.Status.REJECTED)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.committed, 0)
        self.assertEqual(self.order.items.get().reservation.state, InventoryReservation.State.RELEASED)
        events = list(self.order.events.filter(status=Order.Status.REJECTED))
        self.assertEqual(len(events), 1)
        self.assertIn("Cannot prepare this dish", events[0].note)

    def test_reject_paid_online_order_simulates_refund_once(self):
        from orders.services.workflow import reject_order
        from payments.models import PaymentAttempt
        from payments.services import create_payment_attempt, resolve_mock_payment

        add_to_cart(self.buyer, self.listing, self.slot, 1)
        online = checkout(
            self.buyer, idempotency_key="workflow-online",
            payment_method=Order.PaymentMethod.MOCK_CARD,
        )
        attempt = create_payment_attempt(self.buyer, online, idempotency_key="workflow-payment")
        resolve_mock_payment(
            self.buyer, attempt, outcome="succeeded", expected_amount=online.customer_total,
        )
        reject_order(self.owner, online.pk, reason="Kitchen cannot fulfill")
        reject_order(self.owner, online.pk, reason="Kitchen cannot fulfill")
        attempt.refresh_from_db()
        online.refresh_from_db()
        self.stock.refresh_from_db()
        self.assertEqual(online.status, Order.Status.REJECTED)
        self.assertEqual(attempt.state, PaymentAttempt.State.SIMULATED_REFUNDED)
        self.assertEqual(self.stock.committed, 1)
        self.assertEqual(online.events.filter(status=Order.Status.REJECTED).count(), 1)

    def test_buyer_sees_timestamped_seller_progress_after_handoff(self):
        from orders.services.workflow import accept_order, complete_handoff

        accept_order(self.owner, self.order.pk)
        complete_handoff(self.owner, self.order.pk)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("orders:detail", args=[self.order.pk]))
        self.assertContains(response, "Order timeline")
        self.assertContains(response, "Simulated pickup handoff")

    def test_delivery_handoff_collects_simulated_cash_and_preserves_destination(self):
        from orders.services.workflow import accept_order, complete_handoff
        from payments.models import PaymentAttempt

        call_command("seed_locations", verbosity=0)
        origin = DemoLocation.objects.get(code="ari")
        destination = DemoLocation.objects.get(code="asok")
        self.listing.seller.pickup_location = origin
        self.listing.seller.save(update_fields=["pickup_location"])
        add_to_cart(self.buyer, self.listing, self.slot, 1)
        select_fulfillment(self.buyer, Cart.Method.DELIVERY, destination)
        create_quote(self.buyer)
        delivery = checkout(
            self.buyer, idempotency_key="workflow-cash-delivery",
            payment_method=Order.PaymentMethod.CASH_DELIVERY,
        )
        self.listing.seller.pickup_location = DemoLocation.objects.get(code="silom")
        self.listing.seller.save(update_fields=["pickup_location"])
        delivery.refresh_from_db()
        self.assertEqual(delivery.origin_snapshot, "Ari")
        accept_order(self.owner, delivery.pk)
        complete_handoff(self.owner, delivery.pk)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, Order.Status.COMPLETED)
        self.assertEqual(delivery.destination_snapshot, "Asok")
        self.assertEqual(delivery.payment_attempts.get().state, PaymentAttempt.State.CASH_COLLECTED)
        self.assertIn("delivery handoff", delivery.events.last().note)

    def test_order_queue_and_detail_hide_other_sellers_orders(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("orders_workflow:detail", args=[self.order.pk]))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse("orders_workflow:queue"))
        self.assertNotContains(response, self.order.idempotency_key)
        self.client.force_login(self.owner)
        response = self.client.get(reverse("orders_workflow:detail", args=[self.order.pk]))
        self.assertContains(response, self.order.items.get().dish_name_snapshot)

    def test_get_request_cannot_change_order(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("orders_workflow:accept", args=[self.order.pk]))
        self.assertEqual(response.status_code, 405)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CASH_DUE)

    def test_handoff_form_reports_invalid_cash_record_without_completing_order(self):
        from orders.services.workflow import accept_order
        from payments.models import PaymentAttempt

        accept_order(self.owner, self.order.pk)
        PaymentAttempt.objects.create(
            order=self.order, method=Order.PaymentMethod.CASH_PICKUP,
            amount="0.00", idempotency_key="invalid-cash", state=PaymentAttempt.State.CASH_DUE,
        )
        self.client.force_login(self.owner)
        response = self.client.post(reverse("orders_workflow:handoff", args=[self.order.pk]))
        self.assertRedirects(response, reverse("orders_workflow:detail", args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CONFIRMED)
