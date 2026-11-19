from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from catalog.models import FoodListing
from sellers.forms import FoodListingForm


class NutritionValidationTests(SimpleTestCase):
    def listing(self, **kwargs):
        return FoodListing(price=Decimal("100.00"), ingredients=["rice"], **kwargs)

    def test_missing_is_allowed_and_not_zero(self):
        listing = self.listing()
        listing.clean()
        self.assertIsNone(listing.calories_kcal)
        self.assertFalse(listing.has_nutrition)

    def test_complete_reviewed_estimate(self):
        listing = self.listing(calories_kcal=500, serving_size=" 1 bowl (300 g) ",
                               nutrition_source=" Test fixture only ", nutrition_reviewed=True)
        listing.clean()
        self.assertTrue(listing.has_nutrition)
        self.assertEqual(listing.serving_size, "1 bowl (300 g)")

    def test_partial_and_unreviewed_estimates_are_rejected(self):
        for data in [{"calories_kcal": 500}, {"serving_size": "1 bowl"},
                     {"calories_kcal": 500, "serving_size": "1 bowl", "nutrition_source": "Fixture"},
                     {"calories_kcal": 500, "serving_size": "   ", "nutrition_source": "Fixture", "nutrition_reviewed": True}]:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                self.listing(**data).clean()

    def test_calorie_field_rejects_zero_negative_and_excessive_values(self):
        field = FoodListing._meta.get_field("calories_kcal")
        for value in [0, -1, 10001]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                field.clean(value, None)


class NutritionWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.listing = FoodListing.objects.get(dish_id="PK01")

    def payload(self, **changes):
        data = {"dish": self.listing.dish_id, "description": "Food offer", "price": "160.00",
                "status": "published", "ingredients_text": "\n".join(self.listing.ingredients),
                "ingredients_reviewed": "on", "calories_kcal": "500", "serving_size": "1 test bowl (300 g)",
                "nutrition_source": "Automated test fixture, not a nutritional claim", "nutrition_reviewed": "on"}
        data.update(changes)
        return data

    def test_seller_form_saves_and_public_detail_and_card_show_estimate(self):
        form = FoodListingForm(self.payload(), instance=self.listing)
        self.assertTrue(form.is_valid(), form.errors)
        listing = form.save()
        listing.refresh_from_db()
        self.assertTrue(listing.has_nutrition)
        response = self.client.get(reverse("catalog:detail", args=[listing.pk]))
        self.assertContains(response, "Estimated 500 kcal")
        self.assertContains(response, "1 test bowl (300 g)")
        self.assertContains(response, "not a nutritional claim")
        response = self.client.get(reverse("catalog:list"), {"q": "Chicken Biryani"})
        self.assertContains(response, "Estimated 500 kcal")

    def test_partial_submission_is_invalid_without_server_error(self):
        form = FoodListingForm(self.payload(serving_size=""), instance=self.listing)
        self.assertFalse(form.is_valid())
        self.assertIn("serving_size", form.errors)

    def test_changed_ingredients_clear_old_estimate(self):
        form = FoodListingForm(self.payload(), instance=self.listing)
        self.assertTrue(form.is_valid(), form.errors)
        listing = form.save()
        listing.ingredients = listing.ingredients + ["new recipe ingredient"]
        listing.save(update_fields=["ingredients"])
        listing.refresh_from_db()
        self.assertIsNone(listing.calories_kcal)
        self.assertEqual(listing.serving_size, "")
        self.assertEqual(listing.nutrition_source, "")
        self.assertFalse(listing.nutrition_reviewed)

    def test_existing_listing_shows_honest_missing_state(self):
        FoodListing.objects.filter(pk=self.listing.pk).update(
            calories_kcal=None, serving_size="", nutrition_source="", nutrition_reviewed=False)
        response = self.client.get(reverse("catalog:detail", args=[self.listing.pk]))
        self.assertContains(response, "Not provided")
        self.assertNotContains(response, "Estimated 0 kcal")

    def test_seed_preserves_seller_nutrition(self):
        form = FoodListingForm(self.payload(), instance=self.listing)
        self.assertTrue(form.is_valid(), form.errors)
        listing = form.save()
        call_command("seed_catalogue", verbosity=0)
        listing.refresh_from_db()
        self.assertEqual(listing.calories_kcal, 500)
