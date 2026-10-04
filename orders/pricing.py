from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")
DEFAULT_COMMISSION_RATE = Decimal("0.10")


@dataclass(frozen=True)
class OrderTotals:
    food_subtotal: Decimal
    delivery_fee: Decimal
    commission_rate: Decimal
    commission: Decimal
    seller_food_earnings: Decimal
    customer_total: Decimal


def calculate_totals(
    food_subtotal: Decimal,
    delivery_fee: Decimal,
    commission_rate: Decimal = DEFAULT_COMMISSION_RATE,
) -> OrderTotals:
    if food_subtotal < 0 or delivery_fee < 0 or not 0 <= commission_rate <= 1:
        raise ValueError("Totals require nonnegative amounts and a valid commission rate")
    food_subtotal = food_subtotal.quantize(CENT, rounding=ROUND_HALF_UP)
    delivery_fee = delivery_fee.quantize(CENT, rounding=ROUND_HALF_UP)
    commission = (food_subtotal * commission_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    return OrderTotals(
        food_subtotal=food_subtotal,
        delivery_fee=delivery_fee,
        commission_rate=commission_rate,
        commission=commission,
        seller_food_earnings=food_subtotal - commission,
        customer_total=food_subtotal + delivery_fee,
    )
