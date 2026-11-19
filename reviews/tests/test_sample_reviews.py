from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from catalog.models import FoodListing
from reviews.models import Review


class SampleReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        call_command("seed_demo", verbosity=0)
        call_command("seed_sample_reviews", verbosity=0)

    def test_every_dish_gets_four_or_five_approved_reviews(self):
        for listing in FoodListing.objects.public():
            count = Review.objects.public().filter(order__items__listing=listing).count()
            self.assertIn(count, (4, 5), listing.dish_id)

    def test_rerun_does_not_duplicate_reviews(self):
        before = Review.objects.count()
        call_command("seed_sample_reviews", verbosity=0)
        self.assertEqual(Review.objects.count(), before)

    def test_dish_page_and_card_show_reviews(self):
        listing = FoodListing.objects.public().get(dish_id="TH01")
        detail = self.client.get(reverse("catalog:detail", args=[listing.pk]))
        self.assertContains(detail, "Customer reviews")
        card = self.client.get(reverse("catalog:list"), {"q": "Pad Thai"})
        self.assertContains(card, "out of 5")

    def test_sample_ratings_are_positive_but_not_all_perfect(self):
        ratings = set(Review.objects.values_list("rating", flat=True))
        self.assertTrue(ratings <= {4, 5})
        self.assertEqual(ratings, {4, 5})
