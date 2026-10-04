from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from sellers.models import SellerProfile


COUNTRIES = {
    "TH": "Thailand",
    "PK": "Pakistan",
    "BD": "Bangladesh",
    "NP": "Nepal",
    "IN": "India",
}
DIETARY_TAGS = {"vegetarian": "Vegetarian", "vegan": "Vegan"}


def validate_ingredients(value):
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValidationError("Enter at least one nonempty ingredient.")


class Country(models.Model):
    code = models.CharField(max_length=2, primary_key=True)
    name = models.CharField(max_length=40, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def clean(self):
        if COUNTRIES.get(self.code) != self.name:
            raise ValidationError("Country must be one of the five fixed cuisine groups.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Dish(models.Model):
    code = models.CharField(max_length=4, primary_key=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="dishes")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    image_ref = models.CharField(max_length=200, blank=True)
    default_ingredients = models.JSONField(default=list)

    class Meta:
        ordering = ["country__name", "name"]
        constraints = [models.UniqueConstraint(fields=["country", "name"], name="unique_dish_country_name")]

    def clean(self):
        from catalog.manifest import dish_index

        expected = dish_index().get(self.code)
        if not expected or self.country_id != expected["country"] or self.name != expected["name"]:
            raise ValidationError("Choose a dish from the fixed 50-dish catalogue.")
        validate_ingredients(self.default_ingredients)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class FoodListingQuerySet(models.QuerySet):
    def public(self):
        return self.filter(
            status=FoodListing.Status.PUBLISHED,
            seller__status=SellerProfile.Status.APPROVED,
            seller__user__is_active=True,
            ingredients_reviewed=True,
        )


class FoodListing(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    seller = models.ForeignKey(SellerProfile, on_delete=models.PROTECT, related_name="listings")
    dish = models.ForeignKey(Dish, on_delete=models.PROTECT, related_name="listings")
    description = models.TextField(blank=True)
    image = models.FileField(upload_to="listing_images/", blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    ingredients = models.JSONField(default=list)
    dietary_tags = models.JSONField(default=list, blank=True)
    ingredient_version = models.PositiveIntegerField(default=1)
    ingredients_reviewed = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FoodListingQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["seller", "dish"], name="unique_seller_dish"),
            models.CheckConstraint(condition=Q(price__gt=0), name="listing_price_positive"),
        ]
        ordering = ["dish__name", "seller__storefront_name"]

    def clean(self):
        if self.price is not None and self.price <= Decimal("0"):
            raise ValidationError({"price": "Price must be positive."})
        if self.ingredients:
            validate_ingredients(self.ingredients)
        if not isinstance(self.dietary_tags, list) or any(
            tag not in DIETARY_TAGS for tag in self.dietary_tags
        ) or len(self.dietary_tags) != len(set(self.dietary_tags)):
            raise ValidationError({"dietary_tags": "Choose only supported dietary labels."})
        if "vegan" in self.dietary_tags and "vegetarian" not in self.dietary_tags:
            raise ValidationError({"dietary_tags": "Vegan offers must also be labelled vegetarian."})
        if self.status == self.Status.PUBLISHED:
            validate_ingredients(self.ingredients)
            if not self.ingredients_reviewed:
                raise ValidationError("Review ingredients before publishing.")
            if self.seller_id and not self.seller.can_sell:
                raise ValidationError("Only approved active sellers can publish.")

    def save(self, *args, **kwargs):
        updated_fields = kwargs.get("update_fields")
        ingredients_are_saved = updated_fields is None or "ingredients" in updated_fields
        dish_is_saved = updated_fields is None or "dish" in updated_fields or "dish_id" in updated_fields
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values("dish_id", "ingredients", "ingredient_version").first()
            if previous and dish_is_saved and previous["dish_id"] != self.dish_id:
                raise ValidationError({"dish": "An existing offer cannot change its master dish."})
            if previous and ingredients_are_saved and previous["ingredients"] != self.ingredients:
                self.ingredient_version = previous["ingredient_version"] + 1
                self.ingredients_reviewed = False
                self.status = self.Status.DRAFT
                self.dietary_tags = []
                if kwargs.get("update_fields") is not None:
                    kwargs["update_fields"] = set(kwargs["update_fields"]) | {
                        "ingredient_version", "ingredients_reviewed", "status", "dietary_tags"
                    }
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.dish} — {self.seller}"
