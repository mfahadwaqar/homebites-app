from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalog.models import FoodListing
from orders.models import Cart, FulfillmentSlot, Order


class ReviewFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.listing = FoodListing.objects.public().order_by("pk").first()
        cls.seller = cls.listing.seller
        user_model = get_user_model()
        cls.buyer = user_model.objects.create_user(username="review-buyer", password="test-password")
        cls.stranger = user_model.objects.create_user(username="review-stranger", password="test-password")
        cls.staff = user_model.objects.create_user(username="review-staff", password="test-password", is_staff=True)
        start = timezone.now() + timedelta(days=1)
        cls.slot = FulfillmentSlot.objects.create(
            seller=cls.seller, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start, ends_at=start + timedelta(hours=2),
        )
        values = {
            "buyer": cls.buyer, "seller": cls.seller, "slot": cls.slot,
            "payment_method": Order.PaymentMethod.CASH_PICKUP,
            "fulfillment_method": Cart.Method.PICKUP,
            "food_subtotal": Decimal("120.00"), "delivery_fee": Decimal("0.00"),
            "customer_total": Decimal("120.00"), "commission_rate": Decimal("0.1000"),
            "commission": Decimal("12.00"), "seller_food_earnings": Decimal("108.00"),
        }
        cls.completed = Order.objects.create(
            **values, idempotency_key="review-completed", status=Order.Status.COMPLETED,
        )
        cls.confirmed = Order.objects.create(
            **values, idempotency_key="review-confirmed", status=Order.Status.CONFIRMED,
        )


class ReviewRulesTests(ReviewFixture):
    def test_only_completed_order_buyer_can_review_once(self):
        from reviews.models import Review
        from reviews.services import submit_review

        review = submit_review(self.completed, self.buyer, rating=5, comment="A lovely meal")
        self.assertEqual(review.order_id, self.completed.pk)
        self.assertEqual(review.status, Review.Status.PENDING)
        with self.assertRaises(ValidationError):
            submit_review(self.completed, self.buyer, rating=4, comment="Duplicate")
        self.assertEqual(Review.objects.count(), 1)

    def test_other_user_and_incomplete_order_cannot_be_reviewed(self):
        from reviews.services import submit_review

        with self.assertRaises(ValidationError):
            submit_review(self.completed, self.stranger, rating=5, comment="Not my order")
        with self.assertRaises(ValidationError):
            submit_review(self.confirmed, self.buyer, rating=5, comment="Too early")

    def test_rating_outside_one_to_five_is_rejected(self):
        from reviews.services import submit_review

        for rating in (0, 6, None):
            with self.subTest(rating=rating), self.assertRaises(ValidationError):
                submit_review(self.completed, self.buyer, rating=rating, comment="Invalid")

    def test_only_approved_reviews_are_public_and_moderation_is_audited(self):
        from reviews.models import ModerationEvent, Review
        from reviews.services import moderate_review, submit_review

        review = submit_review(self.completed, self.buyer, rating=4, comment="Great flavor")
        self.assertFalse(Review.objects.public().exists())
        with self.assertRaises(ValidationError):
            moderate_review(review, self.stranger, decision="approved", reason="fine")
        moderate_review(review, self.staff, decision="approved", reason="Verified order")
        self.assertEqual(Review.objects.public().count(), 1)
        event = ModerationEvent.objects.get(review=review)
        self.assertEqual(event.actor, self.staff)
        self.assertEqual(event.action, "review_approved")
        self.assertEqual(event.reason, "Verified order")


class ReportRulesTests(ReviewFixture):
    def test_report_must_name_exactly_one_target_and_have_a_reason(self):
        from reviews.models import Report
        from reviews.services import submit_report

        report = submit_report(self.buyer, listing=self.listing, reason="Wrong listing details")
        self.assertEqual(report.status, Report.Status.OPEN)
        self.assertEqual(report.listing_id, self.listing.pk)
        self.assertIsNone(report.seller_id)
        with self.assertRaises(ValidationError):
            submit_report(self.buyer, reason="No target")
        with self.assertRaises(ValidationError):
            submit_report(self.buyer, seller=self.seller, listing=self.listing, reason="Two targets")
        with self.assertRaises(ValidationError):
            submit_report(self.buyer, seller=self.seller, reason=" ")
        self.assertEqual(Report.objects.count(), 1)

    def test_staff_resolution_requires_reason_and_creates_audit_event(self):
        from reviews.models import ModerationEvent, Report
        from reviews.services import resolve_report, submit_report

        report = submit_report(self.buyer, seller=self.seller, reason="Concern about storefront")
        with self.assertRaises(ValidationError):
            resolve_report(report, self.staff, decision="resolved", reason=" ")
        with self.assertRaises(ValidationError):
            resolve_report(report, self.stranger, decision="resolved", reason="Not staff")
        resolve_report(report, self.staff, decision="resolved", reason="Checked storefront")
        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.RESOLVED)
        self.assertEqual(report.resolved_by, self.staff)
        self.assertIsNotNone(report.resolved_at)
        self.assertEqual(
            ModerationEvent.objects.get(report=report).reason, "Checked storefront",
        )
