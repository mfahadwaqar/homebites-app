from django.urls import reverse

from reviews.tests.test_review_rules import ReviewFixture


class ReviewPageTests(ReviewFixture):
    def test_buyer_can_submit_completed_order_review_from_form(self):
        from reviews.models import Review

        url = reverse("reviews:new", args=[self.completed.pk])
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, {"rating": "5", "comment": "Wonderful food"})
        self.assertRedirects(response, reverse("reviews:seller_reviews", args=[self.seller.pk]))
        self.assertEqual(Review.objects.get(order=self.completed).comment, "Wonderful food")

    def test_review_form_rejects_stranger_incomplete_order_and_anonymous(self):
        completed_url = reverse("reviews:new", args=[self.completed.pk])
        confirmed_url = reverse("reviews:new", args=[self.confirmed.pk])
        self.assertEqual(self.client.get(completed_url).status_code, 302)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(completed_url).status_code, 404)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(confirmed_url).status_code, 404)

    def test_public_seller_page_shows_only_approved_reviews_and_average(self):
        from reviews.services import moderate_review, submit_review

        review = submit_review(self.completed, self.buyer, rating=4, comment="Fresh and tasty")
        url = reverse("reviews:seller_reviews", args=[self.seller.pk])
        pending = self.client.get(url)
        self.assertContains(pending, "No published reviews yet")
        self.assertNotContains(pending, "Fresh and tasty")

        moderate_review(review, self.staff, decision="approved", reason="Verified")
        approved = self.client.get(url)
        self.assertContains(approved, "Fresh and tasty")
        self.assertContains(approved, "4.0 / 5")

    def test_report_forms_create_single_target_reports(self):
        from reviews.models import Report

        self.client.force_login(self.buyer)
        seller_url = reverse("reviews:report_seller", args=[self.seller.pk])
        listing_url = reverse("reviews:report_listing", args=[self.listing.pk])
        self.assertEqual(self.client.get(seller_url).status_code, 200)
        self.assertEqual(self.client.get(listing_url).status_code, 200)
        seller_response = self.client.post(seller_url, {"reason": "Seller concern"})
        listing_response = self.client.post(listing_url, {"reason": "Listing concern"})
        self.assertEqual(seller_response.status_code, 302)
        self.assertEqual(listing_response.status_code, 302)
        self.assertTrue(Report.objects.filter(reporter=self.buyer, seller=self.seller, listing__isnull=True).exists())
        self.assertTrue(Report.objects.filter(reporter=self.buyer, listing=self.listing, seller__isnull=True).exists())

    def test_staff_queue_and_post_actions_keep_audit_records(self):
        from reviews.models import ModerationEvent, Report, Review
        from reviews.services import submit_report, submit_review

        review = submit_review(self.completed, self.buyer, rating=5, comment="Good")
        report = submit_report(self.buyer, seller=self.seller, reason="Concern")
        queue = reverse("reviews:moderation_queue")
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(queue).status_code, 403)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(queue), "Concern")
        self.assertRedirects(
            self.client.post(reverse("reviews:moderate_review", args=[review.pk]), {
                "decision": "approved", "reason": "Checked order",
            }), queue,
        )
        self.assertRedirects(
            self.client.post(reverse("reviews:resolve_report", args=[report.pk]), {
                "decision": "dismissed", "reason": "No issue found",
            }), queue,
        )
        review.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(review.status, Review.Status.APPROVED)
        self.assertEqual(report.status, Report.Status.DISMISSED)
        self.assertEqual(ModerationEvent.objects.count(), 2)
