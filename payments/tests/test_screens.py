from django.test import TestCase, override_settings
from django.urls import reverse

from orders.models import Order
from payments.tests.test_payments import PaymentFixture


@override_settings(ROOT_URLCONF="config.urls")
class PaymentScreenTests(PaymentFixture, TestCase):
    def test_promptpay_screen_shows_qr_reference_and_countdown(self):
        order, _, _ = self.make_order(payment_method=Order.PaymentMethod.MOCK_PROMPTPAY)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("payments:pay", args=[order.pk]))
        self.assertContains(response, 'class="mock-qr"')
        self.assertContains(response, "Scan to pay")
        self.assertContains(response, "pay-countdown")
        self.assertContains(response, "paid ฿")

    def test_card_screen_is_a_picture_not_a_form_for_card_details(self):
        order, _, _ = self.make_order(payment_method=Order.PaymentMethod.MOCK_CARD)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("payments:pay", args=[order.pk]))
        self.assertContains(response, "mock-card")
        self.assertContains(response, "No card number, expiry date or security code is requested")
        for forbidden in ('name="card_number"', 'name="cvv"', 'name="expiry"', 'autocomplete="cc-number"'):
            self.assertNotContains(response, forbidden)

    def test_ordinary_customers_get_one_pay_button_and_a_cancel_option_only(self):
        order, _, _ = self.make_order(payment_method=Order.PaymentMethod.MOCK_PROMPTPAY)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("payments:pay", args=[order.pk]))
        self.assertContains(response, "paid ฿")
        self.assertContains(response, "Cancel payment and order")
        for hidden in ("Payment fails", "Payment stays pending", "Decline payment", "Pay later"):
            self.assertNotContains(response, hidden)

    def test_staff_see_no_failure_controls(self):
        from django.contrib.auth import get_user_model
        staff = get_user_model().objects.create_user(username="pay-staff", password="demo-test-pass", is_staff=True)
        order, _, _ = self.make_order(payment_method=Order.PaymentMethod.MOCK_CARD)
        order.buyer = staff
        order.save(update_fields=["buyer"])
        self.client.force_login(staff)
        response = self.client.get(reverse("payments:pay", args=[order.pk]))
        self.assertNotContains(response, "Payment fails")
        self.assertNotContains(response, "Test controls")

    def test_cash_screen_says_pay_on_receipt_and_has_no_simulate_buttons(self):
        order, _, _ = self.make_order(payment_method=Order.PaymentMethod.CASH_PICKUP)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("payments:pay", args=[order.pk]))
        self.assertContains(response, "Pay when you receive it")
        self.assertNotContains(response, "Decline payment")

    def test_order_page_shows_progress_steps_and_receipt_link(self):
        order, _, _ = self.make_order(payment_method=Order.PaymentMethod.CASH_PICKUP)
        self.client.force_login(self.buyer)
        response = self.client.get(reverse("orders:detail", args=[order.pk]))
        self.assertContains(response, "order-steps")
        self.assertContains(response, "Seller confirms")
        self.assertContains(response, reverse("orders:receipt", args=[order.pk]))

    def test_receipt_is_private_to_the_buyer_and_lists_ingredients_and_totals(self):
        order, _, _ = self.make_order(payment_method=Order.PaymentMethod.CASH_PICKUP)
        url = reverse("orders:receipt", args=[order.pk])
        self.client.force_login(self.buyer)
        response = self.client.get(url)
        self.assertContains(response, f"Receipt, order #{order.pk}")
        self.assertContains(response, "฿100.00")
        self.assertContains(response, self.listing.ingredients[0])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
