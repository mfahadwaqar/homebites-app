from django import forms
from pathlib import Path

from catalog.models import DIETARY_TAGS, Dish, FoodListing, validate_ingredients
from fulfillment.models import DemoLocation
from sellers.models import SellerProfile


class SellerApplicationForm(forms.ModelForm):
    class Meta:
        model = SellerProfile
        fields = ["storefront_name", "description", "pickup_location"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["pickup_location"].queryset = DemoLocation.objects.filter(is_active=True, city="Bangkok")


class FoodListingForm(forms.ModelForm):
    MAX_IMAGE_BYTES = 5 * 1024 * 1024
    ALLOWED_IMAGES = {
        ".jpg": ("image/jpeg", lambda head: head.startswith(b"\xff\xd8\xff")),
        ".jpeg": ("image/jpeg", lambda head: head.startswith(b"\xff\xd8\xff")),
        ".png": ("image/png", lambda head: head.startswith(b"\x89PNG\r\n\x1a\n")),
        ".webp": ("image/webp", lambda head: head.startswith(b"RIFF") and head[8:12] == b"WEBP"),
    }

    ingredients_text = forms.CharField(
        label="Your recipe ingredients",
        help_text="Enter one ingredient per line. Review this list before publishing.",
        widget=forms.Textarea(attrs={"rows": 6}),
    )
    ingredients_reviewed = forms.BooleanField(
        required=False,
        label="I reviewed these ingredients for this specific offer",
    )
    dietary_tags = forms.MultipleChoiceField(
        choices=list(DIETARY_TAGS.items()), required=False,
        label="Seller-declared dietary labels",
        help_text="Select only labels supported by your exact ingredient list. These are not allergy or certification claims.",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = FoodListing
        fields = ["dish", "description", "image", "price", "calories_kcal", "serving_size",
                  "nutrition_source", "nutrition_reviewed", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["dish"].queryset = Dish.objects.select_related("country").all()
        self.fields["status"].choices = [
            (FoodListing.Status.DRAFT, "Draft"),
            (FoodListing.Status.PUBLISHED, "Published"),
            (FoodListing.Status.ARCHIVED, "Archived"),
        ]
        if self.instance.pk:
            self.fields["dish"].disabled = True
            self.fields["ingredients_text"].initial = "\n".join(self.instance.ingredients)
            self.fields["ingredients_reviewed"].initial = self.instance.ingredients_reviewed
            self.fields["dietary_tags"].initial = self.instance.dietary_tags

    def clean_dietary_tags(self):
        tags = list(self.cleaned_data["dietary_tags"])
        if "vegan" in tags and "vegetarian" not in tags:
            tags.insert(0, "vegetarian")
        return tags

    def clean_ingredients_text(self):
        ingredients = [line.strip() for line in self.cleaned_data["ingredients_text"].splitlines() if line.strip()]
        validate_ingredients(ingredients)
        return ingredients

    def clean_image(self):
        upload = self.cleaned_data.get("image")
        if not upload or upload == self.instance.image:
            return upload
        if upload.size > self.MAX_IMAGE_BYTES:
            raise forms.ValidationError("Choose an image smaller than 5 MB.")
        extension = Path(upload.name).suffix.lower()
        expected = self.ALLOWED_IMAGES.get(extension)
        if expected is None or getattr(upload, "content_type", None) != expected[0]:
            raise forms.ValidationError("Upload a JPEG, PNG or WebP image with a matching file type.")
        upload.seek(0)
        signature = upload.read(16)
        upload.seek(0)
        if not expected[1](signature):
            raise forms.ValidationError("The uploaded image content does not match its file type.")
        return upload

    def clean(self):
        cleaned = super().clean()
        if "ingredients_text" in cleaned:
            self.instance.ingredients = cleaned["ingredients_text"]
            self.instance.ingredients_reviewed = cleaned.get("ingredients_reviewed", False)
            self.instance.dietary_tags = cleaned.get("dietary_tags", [])
        if cleaned.get("status") == FoodListing.Status.PUBLISHED and not cleaned.get("ingredients_reviewed"):
            self.add_error("ingredients_reviewed", "Review your ingredients before publishing.")
        return cleaned

    def save(self, commit=True):
        listing = super().save(commit=False)
        listing.ingredients = self.cleaned_data["ingredients_text"]
        listing.ingredients_reviewed = self.cleaned_data["ingredients_reviewed"]
        listing.dietary_tags = self.cleaned_data["dietary_tags"]
        if commit:
            changed_recipe = bool(listing.pk) and type(listing).objects.get(pk=listing.pk).ingredients != listing.ingredients
            if changed_recipe:
                # The model invalidates existing review whenever the recipe changes.
                listing.status = FoodListing.Status.DRAFT
            listing.save()
            if changed_recipe and self.cleaned_data["ingredients_reviewed"]:
                listing.ingredients_reviewed = True
                listing.status = self.cleaned_data["status"]
                listing.dietary_tags = self.cleaned_data["dietary_tags"]
                listing.save(update_fields=["ingredients_reviewed", "status", "dietary_tags", "updated_at"])
            self.save_m2m()
        return listing
