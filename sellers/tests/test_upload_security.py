import base64

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import Dish, FoodListing
from sellers.forms import FoodListingForm


PNG_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lXcAAAAASUVORK5CYII="
)


class ListingImageUploadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.dish = Dish.objects.order_by("pk").first()

    def form_with_image(self, name, content, content_type):
        upload = SimpleUploadedFile(name, content, content_type=content_type)
        return FoodListingForm(
            data={
                "dish": self.dish.pk,
                "description": "University demo dish",
                "price": "90.00",
                "status": FoodListing.Status.DRAFT,
                "ingredients_text": "rice\nspices",
            },
            files={"image": upload},
        )

    def test_genuine_small_png_is_accepted_and_read_pointer_is_preserved(self):
        form = self.form_with_image("food.png", PNG_PIXEL, "image/png")

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["image"].read(8), PNG_PIXEL[:8])

    def test_fake_png_payload_is_rejected(self):
        form = self.form_with_image("food.png", b"<script>alert('x')</script>", "image/png")

        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)


    def test_svg_and_mismatched_content_type_are_rejected(self):
        svg = self.form_with_image("food.svg", b"<svg></svg>", "image/svg+xml")
        mismatch = self.form_with_image("food.jpg", PNG_PIXEL, "image/jpeg")

        self.assertFalse(svg.is_valid())
        self.assertFalse(mismatch.is_valid())
        self.assertIn("image", svg.errors)
        self.assertIn("image", mismatch.errors)

    def test_image_over_five_megabytes_is_rejected(self):
        content = PNG_PIXEL + b"0" * (5 * 1024 * 1024)
        form = self.form_with_image("huge.png", content, "image/png")

        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)


class SellerActionSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalogue", verbosity=0)
        cls.own = FoodListing.objects.public().first()
        cls.foreign = FoodListing.objects.public().exclude(seller=cls.own.seller).first()

    def test_edit_requires_csrf_and_own_listing(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.own.seller.user)
        own_url = reverse("sellers:listing_edit", args=[self.own.pk])
        foreign_url = reverse("sellers:listing_edit", args=[self.foreign.pk])
        self.assertEqual(client.get(own_url).status_code, 200)

        denied = client.post(own_url, {"description": "Changed without CSRF"})
        self.assertEqual(denied.status_code, 403)
        self.own.refresh_from_db()
        self.assertNotEqual(self.own.description, "Changed without CSRF")

        token = client.cookies["csrftoken"].value
        foreign = client.post(
            foreign_url,
            {"description": "Unauthorized change", "csrfmiddlewaretoken": token},
        )
        self.assertEqual(foreign.status_code, 404)
        self.foreign.refresh_from_db()
        self.assertNotEqual(self.foreign.description, "Unauthorized change")
