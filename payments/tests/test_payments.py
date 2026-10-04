from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import FulfillmentSlot, InventoryReservation, ListingStock, Order, OrderItem, OrderStatusEvent


class PaymentFixture:
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.listing = FoodListing.objects.public().order_by("pk").first()
        cls.buyer = get_user_model().objects.create_user(username="payment-buyer", password="demo-test-pass")
        cls.other = get_user_model().objects.create_user(username="payment-other", password="demo-test-pass")
        start = timezone.now() + timedelta(hours=2)
        cls.slot = FulfillmentSlot.objects.create(
            seller=cls.listing.seller,
            order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start,
            ends_at=start + timedelta(hours=2),
        )

    def make_order(self, *, payment_method=Order.PaymentMethod.MOCK_CARD):
        cash = payment_method in (Order.PaymentMethod.CASH_PICKUP, Order.PaymentMethod.CASH_DELIVERY)
        stock = ListingStock.objects.create(
            listing=self.listing, slot=self.slot, capacity=1,
            held=0 if cash else 1, committed=1 if cash else 0,
        )
        order = Order.objects.create(
            buyer=self.buyer,
            seller=self.listing.seller,
            slot=self.slot,
            idempotency_key="fixture-order",
            status=Order.Status.CASH_DUE if cash else Order.Status.PENDING_PAYMENT,
            payment_method=payment_method,
            fulfillment_method="pickup",
            food_subtotal=Decimal("100.00"),
            delivery_fee=Decimal("0.00"),
            customer_total=Decimal("100.00"),
            commission_rate=Decimal("0.1000"),
            commission=Decimal("10.00"),
            seller_food_earnings=Decimal("90.00"),
            hold_expires_at=None if cash else timezone.now() + timedelta(minutes=15),
        )
        item = OrderItem.objects.create(
            order=order, listing=self.listing, dish_name_snapshot=self.listing.dish.name,
            country_snapshot=self.listing.dish.country.name,
            ingredients_snapshot=self.listing.ingredients, unit_price=Decimal("100.00"),
            quantity=1, line_total=Decimal("100.00"),
        )
        reservation = InventoryReservation.objects.create(
            item=item, stock=stock, quantity=1,
            state=InventoryReservation.State.COMMITTED if cash else InventoryReservation.State.HELD,
            expires_at=order.hold_expires_at,
        )
        return order, stock, reservation


class SimulatedPaymentTests(PaymentFixture, TestCase):
    def test_success_commits_once_without_confirming_seller(self):
        try:
            from payments.models import PaymentAttempt
            from payments.services import create_payment_attempt, resolve_mock_payment
        except ImportError as exc:
            self.fail(f"Simulated payment service is missing: {exc}")

        order, stock, reservation = self.make_order()
        attempt = create_payment_attempt(self.buyer, order, idempotency_key="attempt-one")
        first = resolve_mock_payment(
            self.buyer, attempt, outcome="succeeded", expected_amount=Decimal("100.00"),
        )
        second = resolve_mock_payment(
            self.buyer, attempt, outcome="succeeded", expected_amount=Decimal("100.00"),
        )

        stock.refresh_from_db()
        reservation.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(PaymentAttempt.objects.count(), 1)
        self.assertEqual(first.state, PaymentAttempt.State.SUCCEEDED)
        self.assertEqual(order.status, Order.Status.AWAITING_SELLER)
        self.assertEqual((stock.held, stock.committed), (0, 1))
        self.assertEqual(reservation.state, InventoryReservation.State.COMMITTED)
        self.assertTrue(attempt.mock_reference.startswith("DEMO-"))
        self.assertTrue(OrderStatusEvent.objects.filter(order=order, status=Order.Status.AWAITING_SELLER).exists())

    def test_failure_releases_once_and_retry_cannot_resurrect_order(self):
        from payments.models import PaymentAttempt
        from payments.services import PaymentConflict, create_payment_attempt, resolve_mock_payment

        order, stock, reservation = self.make_order()
        attempt = create_payment_attempt(self.buyer, order, idempotency_key="attempt-fail")
        resolve_mock_payment(self.buyer, attempt, outcome="failed", expected_amount=Decimal("100.00"))
        resolve_mock_payment(self.buyer, attempt, outcome="failed", expected_amount=Decimal("100.00"))
        with self.assertRaises(PaymentConflict):
            resolve_mock_payment(self.buyer, attempt, outcome="succeeded", expected_amount=Decimal("100.00"))

        stock.refresh_from_db()
        reservation.refresh_from_db()
        order.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(attempt.state, PaymentAttempt.State.FAILED)
        self.assertEqual(order.status, Order.Status.PAYMENT_FAILED)
        self.assertEqual((stock.held, stock.committed), (0, 0))
        self.assertEqual(reservation.state, InventoryReservation.State.RELEASED)
        self.assertEqual(OrderStatusEvent.objects.filter(order=order, status=Order.Status.PAYMENT_FAILED).count(), 1)

    def test_late_success_cannot_resurrect_expired_hold(self):
        from payments.services import PaymentConflict, create_payment_attempt, resolve_mock_payment

        order, stock, _ = self.make_order()
        attempt = create_payment_attempt(self.buyer, order, idempotency_key="attempt-late")
        with self.assertRaises(PaymentConflict):
            resolve_mock_payment(
                self.buyer, attempt, outcome="succeeded", expected_amount=Decimal("100.00"),
                now=order.hold_expires_at + timedelta(seconds=1),
            )
        order.refresh_from_db()
        stock.refresh_from_db()
        self.assertNotEqual(order.status, Order.Status.AWAITING_SELLER)
        self.assertEqual(stock.committed, 0)

    def test_wrong_buyer_or_wrong_amount_cannot_resolve(self):
        from payments.services import PaymentConflict, create_payment_attempt, resolve_mock_payment

        order, _, _ = self.make_order()
        attempt = create_payment_attempt(self.buyer, order, idempotency_key="attempt-guard")
        with self.assertRaises(PaymentConflict):
            resolve_mock_payment(self.other, attempt, outcome="succeeded", expected_amount=Decimal("100.00"))
        with self.assertRaises(PaymentConflict):
            resolve_mock_payment(self.buyer, attempt, outcome="succeeded", expected_amount=Decimal("99.00"))
        with self.assertRaises(PaymentConflict):
            resolve_mock_payment(self.buyer, attempt, outcome="succeeded", expected_amount="not-an-amount")

    def test_cash_collection_requires_seller_and_is_idempotent(self):
        from payments.models import PaymentAttempt
        from payments.services import PaymentConflict, payment_is_confirmable, record_cash_collection

        order, stock, _ = self.make_order(payment_method=Order.PaymentMethod.CASH_PICKUP)
        self.assertTrue(payment_is_confirmable(order))
        self.assertFalse(PaymentAttempt.objects.filter(order=order).exists())
        with self.assertRaises(PaymentConflict):
            record_cash_collection(self.other, order)
        with self.assertRaises(PaymentConflict):
            record_cash_collection(self.listing.seller.user, order)
        order.status = Order.Status.CONFIRMED
        order.save(update_fields=["status"])
        record_cash_collection(self.listing.seller.user, order)
        record_cash_collection(self.listing.seller.user, order)
        attempt = PaymentAttempt.objects.get(order=order)
        attempt.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(attempt.state, PaymentAttempt.State.CASH_COLLECTED)
        self.assertEqual((stock.held, stock.committed), (0, 1))

    def test_simulated_refund_records_state_without_real_money(self):
        from payments.models import PaymentAttempt
        from payments.services import create_payment_attempt, resolve_mock_payment, simulate_refund

        order, _, _ = self.make_order()
        attempt = create_payment_attempt(self.buyer, order, idempotency_key="attempt-refund")
        resolve_mock_payment(self.buyer, attempt, outcome="succeeded", expected_amount=Decimal("100.00"))
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status"])
        simulate_refund(order)
        simulate_refund(order)
        attempt.refresh_from_db()
        self.assertEqual(attempt.state, PaymentAttempt.State.SIMULATED_REFUNDED)

    def test_staff_can_inspect_payment_records_but_not_edit_them_in_admin(self):
        from payments.services import create_payment_attempt

        order, _, _ = self.make_order()
        attempt = create_payment_attempt(self.buyer, order, idempotency_key="admin-inspection")
        staff = get_user_model().objects.create_superuser(username="payment-admin", password="demo-test-pass")
        self.client.force_login(staff)
        response = self.client.get(reverse("admin:payments_paymentattempt_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, attempt.mock_reference)
        response = self.client.post(
            reverse("admin:payments_paymentattempt_change", args=[attempt.pk]),
            {"state": "succeeded", "_save": "Save"},
        )
        self.assertEqual(response.status_code, 403)


from django.test import override_settings
from django.urls import reverse


@override_settings(ROOT_URLCONF="payments.tests.urls")
class PaymentPageTests(PaymentFixture, TestCase):
    def test_online_page_uses_only_fake_controls_and_result_post(self):
        from payments.models import PaymentAttempt

        order, stock, _ = self.make_order(payment_method=Order.PaymentMethod.MOCK_PROMPTPAY)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("payments:pay", args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DEMO")
        self.assertNotContains(response, 'name="card_number"')
        self.assertNotContains(response, 'name="cvv"')
        self.assertEqual(PaymentAttempt.objects.filter(order=order).count(), 1)

        response = self.client.post(
            reverse("payments:result", args=[order.pk]),
            {"outcome": "succeeded", "amount": "100.00"},
        )
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(order.status, Order.Status.AWAITING_SELLER)
        self.assertEqual((stock.held, stock.committed), (0, 1))

    def test_other_buyer_cannot_open_or_submit_payment(self):
        order, _, _ = self.make_order()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("payments:pay", args=[order.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("payments:result", args=[order.pk]), {"outcome": "succeeded"}).status_code, 404)

    def test_expired_order_does_not_show_payment_result_controls(self):
        from payments.services import create_payment_attempt

        order, _, _ = self.make_order()
        create_payment_attempt(self.buyer, order, idempotency_key="expired-screen")
        order.status = Order.Status.EXPIRED
        order.save(update_fields=["status"])
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("payments:pay", args=[order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Simulate success")
