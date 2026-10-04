from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from fulfillment.models import DemoLocation
from sellers.models import SellerProfile


class DietaryDeclarationTests(TestCase):
    def test_seller_can_declare_vegan_offer_without_changing_ingredients(self):
        from catalog.models import FoodListing
        from sellers.forms import FoodListingForm

        call_command("seed_catalogue", verbosity=0)
        listing = FoodListing.objects.get(dish_id="IN05")
        form = FoodListingForm(data={
            "dish": listing.dish_id,
            "description": listing.description,
            "price": str(listing.price),
            "status": "published",
            "ingredients_text": "\n".join(listing.ingredients),
            "ingredients_reviewed": "on",
            "dietary_tags": ["vegan"],
        }, instance=listing)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        listing.refresh_from_db()
        self.assertCountEqual(listing.dietary_tags, ["vegetarian", "vegan"])


class SellerApplicationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="cook", password="test-password")

    def test_signed_in_user_applies_once_and_waits_for_approval(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("sellers:apply"), {
            "storefront_name": "Kitchen One", "description": "Bangkok home cook",
        })
        self.assertRedirects(response, reverse("sellers:dashboard"))
        profile = SellerProfile.objects.get(user=self.user)
        self.assertEqual(profile.status, SellerProfile.Status.PENDING)
        self.client.post(reverse("sellers:apply"), {
            "storefront_name": "Duplicate", "description": "Second application",
        })
        self.assertEqual(SellerProfile.objects.filter(user=self.user).count(), 1)
        self.assertEqual(profile.storefront_name, "Kitchen One")

    def test_anonymous_user_cannot_apply(self):
        response = self.client.get(reverse("sellers:apply"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SellerProfile.objects.count(), 0)

    def test_staff_can_approve_seller_in_admin(self):
        self.client.force_login(self.user)
        self.client.post(reverse("sellers:apply"), {
            "storefront_name": "Kitchen One", "description": "Bangkok home cook",
        })
        staff = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.local", password="admin-password",
        )
        self.client.force_login(staff)
        profile = SellerProfile.objects.get(user=self.user)
        response = self.client.post(
            reverse("admin:sellers_sellerprofile_changelist"),
            {"action": "approve_sellers", "_selected_action": [profile.pk]},
        )
        self.assertEqual(response.status_code, 302)
        profile.refresh_from_db()
        self.assertEqual(profile.status, SellerProfile.Status.APPROVED)

    def test_seller_can_reference_a_demo_pickup_location(self):
        location = DemoLocation.objects.create(
            code="ari", label="Ari", latitude="13.779700", longitude="100.544800",
        )
        profile = SellerProfile.objects.create(user=self.user, storefront_name="Kitchen One")
        profile.pickup_location = location
        profile.save()
        saved = SellerProfile.objects.get(pk=profile.pk)
        self.assertEqual(saved.pickup_location_id, location.pk)

    def test_seller_can_update_own_storefront_and_pickup_location(self):
        location = DemoLocation.objects.create(
            code="ari", label="Ari", latitude="13.779700", longitude="100.544800",
        )
        profile = SellerProfile.objects.create(user=self.user, storefront_name="Kitchen One")
        self.client.force_login(self.user)
        response = self.client.post(reverse("sellers:profile_edit"), {
            "storefront_name": "Updated Kitchen", "description": "New description",
            "pickup_location": location.pk,
        })
        self.assertRedirects(response, reverse("sellers:dashboard"))
        profile.refresh_from_db()
        self.assertEqual(profile.storefront_name, "Updated Kitchen")
        self.assertEqual(profile.pickup_location_id, location.pk)
