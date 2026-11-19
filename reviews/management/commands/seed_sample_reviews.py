"""Create fictional completed orders and approved reviews so dish pages have sample reviews."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import FulfillmentSlot, Order, OrderItem, OrderStatusEvent
from reviews.models import Review
from reviews.sample_reviews import COMMENTS, FIFTH, RATINGS, REVIEWERS

PREFIX = "sample_"


class Command(BaseCommand):
    help = "Seed 4-5 fictional approved reviews per dish. Safe to re-run; --reset removes them first."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete sample reviews and their orders first.")

    def handle(self, *args, **options):
        User = get_user_model()
        if options["reset"]:
            orders = Order.objects.filter(buyer__username__startswith=PREFIX)
            Review.objects.filter(order__in=orders).delete()
            OrderStatusEvent.objects.filter(order__in=orders).delete()
            OrderItem.objects.filter(order__in=orders).delete()
            orders.delete()
        users = []
        for first, last in REVIEWERS:
            user, created = User.objects.get_or_create(
                username=f"{PREFIX}{first.lower()}_{last.lower().strip('.')}",
                defaults={"first_name": first, "last_name": last, "email": ""},
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            users.append(user)
        now = timezone.now()
        created_count = 0
        listings = FoodListing.objects.public().select_related("dish", "seller").order_by("dish__code", "pk")
        for listing in listings:
            code = listing.dish_id
            comments = list(COMMENTS.get(code, []))
            if not comments:
                continue
            if int(code[2:]) % 2:
                comments.append(FIFTH[(int(code[2:]) // 2) % len(FIFTH)])
            if Review.objects.filter(order__items__listing=listing, order__buyer__username__startswith=PREFIX).exists():
                continue
            slot = FulfillmentSlot.objects.filter(seller=listing.seller).order_by("pk").first()
            if slot is None:
                continue
            start = (sum(ord(c) for c in code) % len(users))
            with transaction.atomic():
                for i, comment in enumerate(comments):
                    buyer = users[(start + i * 3) % len(users)]
                    quantity = 1 + (i % 2)
                    subtotal = listing.price * quantity
                    commission = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))
                    order = Order.objects.create(
                        buyer=buyer, seller=listing.seller, slot=slot,
                        idempotency_key=f"sample-{listing.pk}-{i}", status=Order.Status.COMPLETED,
                        payment_method=Order.PaymentMethod.CASH_PICKUP, fulfillment_method="pickup",
                        food_subtotal=subtotal, delivery_fee=Decimal("0.00"), customer_total=subtotal,
                        commission_rate=Decimal("0.1000"), commission=commission,
                        seller_food_earnings=subtotal - commission,
                    )
                    OrderItem.objects.create(
                        order=order, listing=listing, dish_name_snapshot=listing.dish.name,
                        country_snapshot=listing.dish.country.name, ingredients_snapshot=list(listing.ingredients),
                        unit_price=listing.price, quantity=quantity, line_total=subtotal,
                    )
                    review = Review.objects.create(
                        order=order, rating=RATINGS[i % len(RATINGS)], comment=comment,
                        status=Review.Status.APPROVED,
                    )
                    when = now - timedelta(days=3 + (sum(ord(c) for c in code) * (i + 2)) % 38, hours=i * 5)
                    Order.objects.filter(pk=order.pk).update(created_at=when, updated_at=when)
                    Review.objects.filter(pk=review.pk).update(created_at=when, updated_at=when)
                    created_count += 1
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} sample reviews (fictional customers, demo data)."))
