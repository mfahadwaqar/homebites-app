from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from catalog.models import Country, Dish, FoodListing
from catalog.manifest import load_manifest, validate_manifest, validate_manifest_document
from sellers.models import SellerProfile


class CatalogueSeedTests(TestCase):
    def test_seed_refuses_to_approve_a_registered_account_with_demo_username(self):
        user = get_user_model().objects.create_user(
            username="demo_seller_thailand", password="real-user-password",
        )
        with self.assertRaises(CommandError):
            call_command("seed_catalogue")
        self.assertFalse(SellerProfile.objects.filter(user=user).exists())

    def test_seed_has_exactly_five_countries_ten_dishes_each_and_fifty_offers(self):
        call_command("seed_catalogue")
        self.assertEqual(Country.objects.count(), 5)
        self.assertEqual(Dish.objects.count(), 50)
        self.assertEqual(FoodListing.objects.public().count(), 50)
        for country in Country.objects.all():
            self.assertEqual(country.dishes.count(), 10)
        self.assertTrue(all(listing.ingredients for listing in FoodListing.objects.all()))
        self.assertIn("vegan", FoodListing.objects.get(dish_id="IN05").dietary_tags)

    def test_seed_is_repeatable_without_overwriting_seller_recipe(self):
        call_command("seed_catalogue")
        listing = FoodListing.objects.order_by("pk").first()
        listing.ingredients = ["a family recipe ingredient"]
        listing.save()
        call_command("seed_catalogue")
        listing.refresh_from_db()
        self.assertEqual(listing.ingredients, ["a family recipe ingredient"])
        self.assertEqual(Dish.objects.count(), 50)
        self.assertEqual(FoodListing.objects.count(), 50)


class ManifestTests(SimpleTestCase):
    def test_unknown_manifest_version_is_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            validate_manifest_document({"version": "unreviewed", "dishes": load_manifest()})

    def test_manifest_validation_does_not_depend_on_row_order(self):
        validate_manifest(list(reversed(load_manifest())))

    def test_nonpositive_offer_price_is_rejected_before_seed(self):
        rows = [dict(row) for row in load_manifest()]
        rows[0]["price"] = "-1.00"
        with self.assertRaises(ImproperlyConfigured):
            validate_manifest(rows)

    def test_offer_price_that_exceeds_listing_field_is_rejected_before_seed(self):
        rows = [dict(row) for row in load_manifest()]
        rows[0]["price"] = "10000000.00"
        with self.assertRaises(ImproperlyConfigured):
            validate_manifest(rows)

    def test_unknown_country_is_rejected_before_seed(self):
        rows = [dict(row) for row in load_manifest()]
        rows[0]["country"] = "XX"
        with self.assertRaises(ImproperlyConfigured):
            validate_manifest(rows)


class ListingRulesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue")
        cls.dish = Dish.objects.get(code="TH01")
        cls.owner = SellerProfile.objects.get(user__username="demo_seller_thailand")
        cls.other_user = get_user_model().objects.create_user(
            username="other", password="test-password",
        )
        cls.other_seller = SellerProfile.objects.create(
            user=cls.other_user, storefront_name="Other Kitchen", status=SellerProfile.Status.APPROVED,
        )

    def test_recipe_edit_clears_dietary_claim_until_reviewed_again(self):
        listing = FoodListing.objects.get(dish_id="IN05")
        self.assertIn("vegan", listing.dietary_tags)
        listing.ingredients = ["changed ingredient"]
        listing.save()
        listing.refresh_from_db()
        self.assertEqual(listing.dietary_tags, [])
        self.assertEqual(listing.status, FoodListing.Status.DRAFT)

    def test_two_sellers_can_offer_same_dish_with_distinct_ingredients(self):
        second = FoodListing.objects.create(
            seller=self.other_seller, dish=self.dish, price=Decimal("120.00"),
            ingredients=["tofu", "chilli"], ingredients_reviewed=True,
            status=FoodListing.Status.PUBLISHED,
        )
        first = FoodListing.objects.get(seller=self.owner, dish=self.dish)
        self.assertNotEqual(first.ingredients, second.ingredients)
        self.assertEqual(Dish.objects.count(), 50)

    def test_published_listing_needs_reviewed_nonempty_ingredients(self):
        with self.assertRaises(ValidationError):
            FoodListing.objects.create(
                seller=self.other_seller, dish=self.dish, price=Decimal("120.00"),
                ingredients=[], ingredients_reviewed=True, status=FoodListing.Status.PUBLISHED,
            )
        with self.assertRaises(ValidationError):
            FoodListing.objects.create(
                seller=self.other_seller, dish=self.dish, price=Decimal("120.00"),
                ingredients=["tofu"], ingredients_reviewed=False,
                status=FoodListing.Status.PUBLISHED,
            )

    def test_pending_or_suspended_seller_cannot_publish(self):
        for status in (SellerProfile.Status.PENDING, SellerProfile.Status.SUSPENDED):
            self.other_seller.status = status
            self.other_seller.save()
            with self.assertRaises(ValidationError):
                FoodListing.objects.create(
                    seller=self.other_seller, dish=self.dish, price=Decimal("120.00"),
                    ingredients=["tofu"], ingredients_reviewed=True,
                    status=FoodListing.Status.PUBLISHED,
                )

    def test_ingredient_change_increments_version_and_requires_fresh_review(self):
        listing = FoodListing.objects.get(seller=self.owner, dish=self.dish)
        previous_version = listing.ingredient_version
        listing.ingredients = ["new ingredient"]
        listing.save()
        listing.refresh_from_db()
        self.assertEqual(listing.ingredient_version, previous_version + 1)
        self.assertFalse(listing.ingredients_reviewed)
        self.assertEqual(listing.status, FoodListing.Status.DRAFT)

    def test_price_only_update_does_not_publish_unsaved_ingredient_edit(self):
        listing = FoodListing.objects.get(seller=self.owner, dish=self.dish)
        original_ingredients = list(listing.ingredients)
        listing.ingredients = ["not saved"]
        listing.price = Decimal("140.00")
        listing.save(update_fields=["price"])
        listing.refresh_from_db()
        self.assertEqual(listing.ingredients, original_ingredients)
        self.assertEqual(listing.ingredient_version, 1)
        self.assertTrue(listing.ingredients_reviewed)
        self.assertEqual(listing.status, FoodListing.Status.PUBLISHED)

    def test_existing_offer_cannot_change_its_master_dish(self):
        listing = FoodListing.objects.get(seller=self.owner, dish=self.dish)
        listing.dish = Dish.objects.get(code="PK01")
        with self.assertRaises(ValidationError):
            listing.save()

    def test_listing_owner_can_edit_but_other_seller_cannot(self):
        listing = FoodListing.objects.get(seller=self.owner, dish=self.dish)
        self.client.force_login(self.other_user)
        response = self.client.post(reverse("sellers:listing_edit", args=[listing.pk]), {
            "dish": self.dish.pk, "description": "Stolen edit", "price": "9.00",
            "ingredients_text": "tofu", "ingredients_reviewed": "on", "status": "published",
        })
        self.assertEqual(response.status_code, 404)
        listing.refresh_from_db()
        self.assertNotEqual(listing.description, "Stolen edit")

    def test_seller_cannot_submit_unknown_master_dish(self):
        self.client.force_login(self.other_user)
        response = self.client.post(reverse("sellers:listing_create"), {
            "dish": 999999, "price": "120.00", "ingredients_text": "tofu",
            "ingredients_reviewed": "on", "status": "published",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Select a valid choice")
        self.assertEqual(FoodListing.objects.filter(seller=self.other_seller).count(), 0)

    def test_approved_seller_can_publish_reviewed_recipe(self):
        self.client.force_login(self.other_user)
        response = self.client.post(reverse("sellers:listing_create"), {
            "dish": self.dish.pk, "description": "Family recipe", "price": "125.00",
            "ingredients_text": "tofu\nchilli", "ingredients_reviewed": "on", "status": "published",
        })
        if response.status_code == 200:
            self.fail(str(response.context["form"].errors))
        self.assertRedirects(response, reverse("sellers:dashboard"))
        listing = FoodListing.objects.get(seller=self.other_seller, dish=self.dish)
        self.assertEqual(listing.ingredients, ["tofu", "chilli"])
        self.assertTrue(listing.ingredients_reviewed)
        self.assertEqual(listing.status, FoodListing.Status.PUBLISHED)
        self.assertEqual(listing.dish.default_ingredients, ["rice noodles", "tamarind", "egg", "bean sprouts", "peanuts"])

    def test_reviewed_recipe_edit_advances_version_and_remains_publishable(self):
        self.client.force_login(self.other_user)
        listing = FoodListing.objects.create(
            seller=self.other_seller, dish=self.dish, price=Decimal("125.00"),
            ingredients=["tofu"], ingredients_reviewed=True, status=FoodListing.Status.PUBLISHED,
        )
        response = self.client.post(reverse("sellers:listing_edit", args=[listing.pk]), {
            "dish": self.dish.pk, "description": "Updated recipe", "price": "130.00",
            "ingredients_text": "tofu\nchilli", "ingredients_reviewed": "on", "status": "published",
        })
        self.assertRedirects(response, reverse("sellers:dashboard"))
        listing.refresh_from_db()
        self.assertEqual(listing.ingredient_version, 2)
        self.assertEqual(listing.ingredients, ["tofu", "chilli"])
        self.assertTrue(listing.ingredients_reviewed)
        self.assertEqual(listing.status, FoodListing.Status.PUBLISHED)
