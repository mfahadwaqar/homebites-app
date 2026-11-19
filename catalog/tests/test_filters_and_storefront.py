from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from catalog.models import FoodListing
from orders.models import Order
from reviews.models import Review


class FilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        call_command("seed_demo", verbosity=0)
        call_command("seed_sample_reviews", verbosity=0)

    def codes(self, **params):
        response = self.client.get(reverse("catalog:list"), params)
        self.assertEqual(response.status_code, 200)
        return [listing.dish_id for listing in response.context["page_obj"].object_list]

    def test_dessert_category_lists_only_desserts(self):
        response = self.client.get(reverse("catalog:list"), {"category": "dessert"})
        self.assertEqual(response.context["page_obj"].paginator.count, 6)
        self.assertContains(response, "Desserts")

    def test_pickup_area_filter_matches_the_seller_pickup_point(self):
        listing = FoodListing.objects.public().select_related("seller__pickup_location").first()
        area = listing.seller.pickup_location_id
        response = self.client.get(reverse("catalog:list"), {"area": area})
        expected = FoodListing.objects.public().filter(seller__pickup_location_id=area).count()
        self.assertEqual(response.context["page_obj"].paginator.count, expected)
        self.assertGreater(expected, 0)

    def test_minimum_rating_filter_keeps_only_well_rated_offers(self):
        Review.objects.filter(order__items__listing__dish_id="TH01").update(rating=3)
        everything = self.client.get(reverse("catalog:list")).context["page_obj"].paginator.count
        rated = self.client.get(reverse("catalog:list"), {"min_rating": "4.5"}).context["page_obj"].paginator.count
        self.assertLess(rated, everything)
        self.assertNotIn("TH01", self.codes(min_rating="4"))

    def test_sort_by_price_both_ways(self):
        low = self.client.get(reverse("catalog:list"), {"sort": "price_asc"}).context["page_obj"].object_list
        high = self.client.get(reverse("catalog:list"), {"sort": "price_desc"}).context["page_obj"].object_list
        self.assertLessEqual(low[0].price, low[len(low) - 1].price)
        self.assertGreaterEqual(high[0].price, high[len(high) - 1].price)

    def test_sort_by_rating_and_bad_values_do_not_crash(self):
        self.assertEqual(self.client.get(reverse("catalog:list"), {"sort": "rating"}).status_code, 200)
        self.assertEqual(self.client.get(reverse("catalog:list"), {"min_rating": "x", "area": "zz", "category": "??", "sort": "nope"}).status_code, 200)

    def test_storefront_shows_rating_completed_orders_and_reviews(self):
        seller = FoodListing.objects.public().get(dish_id="PK01").seller
        page = self.client.get(reverse("sellers:storefront", args=[seller.pk]))
        self.assertContains(page, "out of 5 average rating")
        self.assertContains(page, "completed orders")
        self.assertContains(page, "What customers say")
        completed = Order.objects.filter(seller=seller, status=Order.Status.COMPLETED).count()
        self.assertContains(page, f"<strong>{completed}</strong>")


class ProfileAndDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.user = get_user_model().objects.create_user(username="edit-me", password="safe-test-pass-2026", email="old@example.test")

    def test_profile_can_be_edited_and_has_no_placeholder(self):
        self.client.force_login(self.user)
        page = self.client.get(reverse("accounts:profile"))
        self.assertNotContains(page, "later milestones")
        self.assertContains(page, "Change your password")
        response = self.client.post(reverse("accounts:profile"), {"display_name": "New Name", "email": "new@example.test"})
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual((self.user.display_name, self.user.email), ("New Name", "new@example.test"))

    def test_password_change_pages_exist(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("password_change")), "Change your password")


class OfferDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        call_command("seed_demo", verbosity=0)

    def setUp(self):
        self.listing = FoodListing.objects.public().get(dish_id="TH02")
        self.owner = self.listing.seller.user
        self.owner.set_password("seller-test-pass-2026")
        self.owner.save()
        self.client.force_login(self.owner)

    def test_offer_without_orders_is_deleted(self):
        response = self.client.post(reverse("sellers:listing_delete", args=[self.listing.pk]))
        self.assertRedirects(response, reverse("sellers:dashboard"))
        self.assertFalse(FoodListing.objects.filter(pk=self.listing.pk).exists())

    def test_offer_with_order_history_is_unpublished_not_deleted(self):
        from orders.models import OrderItem
        busy = FoodListing.objects.public().get(dish_id="PK01")
        self.client.force_login(busy.seller.user)
        from django.core.management import call_command as cc
        cc("seed_sample_reviews", verbosity=0)
        self.assertTrue(OrderItem.objects.filter(listing=busy).exists())
        self.client.post(reverse("sellers:listing_delete", args=[busy.pk]))
        busy.refresh_from_db()
        self.assertEqual(busy.status, FoodListing.Status.DRAFT)

    def test_other_sellers_cannot_delete_it(self):
        other = FoodListing.objects.public().exclude(seller=self.listing.seller).first().seller.user
        self.client.force_login(other)
        self.assertEqual(self.client.post(reverse("sellers:listing_delete", args=[self.listing.pk])).status_code, 404)
