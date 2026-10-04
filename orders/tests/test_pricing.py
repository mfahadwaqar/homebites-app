from decimal import Decimal

from django.test import SimpleTestCase


class OrderPricingTests(SimpleTestCase):
    def test_delivery_is_separate_from_ten_percent_food_commission(self):
        try:
            from orders.pricing import calculate_totals
        except ImportError:
            self.fail("Order totals service is missing")

        totals = calculate_totals(Decimal("500.00"), Decimal("50.00"))

        self.assertEqual(totals.commission, Decimal("50.00"))
        self.assertEqual(totals.seller_food_earnings, Decimal("450.00"))
        self.assertEqual(totals.customer_total, Decimal("550.00"))

    def test_commission_uses_half_up_money_rounding(self):
        try:
            from orders.pricing import calculate_totals
        except ImportError:
            self.fail("Order totals service is missing")

        totals = calculate_totals(Decimal("0.05"), Decimal("0.00"))

        self.assertEqual(totals.commission, Decimal("0.01"))
        self.assertEqual(totals.seller_food_earnings, Decimal("0.04"))

