from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
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
DIETARY_TAGS = {"vegetarian": "Vegetarian", "vegan": "Vegan", "halal": "Halal"}


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


DISH_CATEGORIES = {"main": "Main dishes", "snack": "Snacks and street food", "dessert": "Desserts"}
DESSERT_CODES = {"TH10", "PK10", "BD10", "NP07", "NP10", "IN10"}
SNACK_CODES = {"PK05", "PK09", "BD09", "NP01", "NP03", "NP06", "IN08"}


def category_for(code):
    return "dessert" if code in DESSERT_CODES else "snack" if code in SNACK_CODES else "main"


class Dish(models.Model):
    code = models.CharField(max_length=4, primary_key=True)
    category = models.CharField(max_length=10, choices=list(DISH_CATEGORIES.items()), default="main", db_index=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="dishes")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    image_ref = models.CharField(max_length=200, blank=True)
    default_ingredients = models.JSONField(default=list)

    @property
    def illustrative_image(self):
        """Local cuisine photo for offers without a seller-supplied photograph."""
        from catalog.photos import photo_for_dish
        photo = photo_for_dish(self.code)
        if photo:
            return photo["path"]
        if self.code == "PK01":
            return "catalog/food/hero-biryani.webp"
        return f"catalog/food/{COUNTRIES[self.country_id].lower()}.webp"

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
    calories_kcal = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10000)],
        verbose_name="Estimated kcal per serving",
        help_text="Use a documented estimate for this recipe, not a value inferred from its name or photo.",
    )
    serving_size = models.CharField(max_length=120, blank=True,
        help_text="Describe the serving, for example 1 bowl (300 g).")
    nutrition_source = models.CharField(max_length=300, blank=True,
        help_text="Recipe URL, package reference, or documented seller estimate and calculation basis.")
    nutrition_reviewed = models.BooleanField(default=False,
        help_text="Confirm that the serving size and estimate apply to the ingredients in this offer.")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = FoodListingQuerySet.as_manager()

    @property
    def has_nutrition(self):
        return bool(self.calories_kcal and self.serving_size.strip()
                    and self.nutrition_source.strip() and self.nutrition_reviewed)

    @property
    def catalogue_photo(self):
        from catalog.photos import photo_for_dish
        # Never attribute a catalogue credit to a seller upload, and never show a
        # photograph that contradicts a seller-declared diet. Each record carries
        # an optional "diet" ("vegan" or "vegetarian") only when the pictured dish
        # contains no meat, fish or (for vegan) dairy/egg.
        if self.image:
            return None
        photo = photo_for_dish(self.dish_id)
        meat_free = [tag for tag in self.dietary_tags if tag in ("vegetarian", "vegan")]
        if not photo or not meat_free:
            return photo
        allowed = {"vegan"} if "vegan" in meat_free else {"vegan", "vegetarian"}
        return photo if photo.get("diet") in allowed else None

    @property
    def illustrative_image(self):
        photo = self.catalogue_photo
        if photo:
            return photo["path"]
        if "vegetarian" in self.dietary_tags or "vegan" in self.dietary_tags:
            if self.dish.code == "TH01" and "vegan" not in self.dietary_tags:
                return "catalog/food/pad-thai-vegetarian.webp"
            return f"catalog/food/{COUNTRIES[self.dish.country_id].lower()}-vegetarian.webp"
        return self.dish.illustrative_image

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["seller", "dish"], name="unique_seller_dish"),
            models.CheckConstraint(condition=Q(price__gt=0), name="listing_price_positive"),
            models.CheckConstraint(condition=Q(calories_kcal__isnull=True) | Q(calories_kcal__gte=1, calories_kcal__lte=10000), name="listing_calories_valid"),
        ]
        ordering = ["dish__name", "seller__storefront_name"]

    def clean(self):
        self.serving_size = self.serving_size.strip()
        self.nutrition_source = self.nutrition_source.strip()
        nutrition = {
            "calories_kcal": self.calories_kcal is not None,
            "serving_size": bool(self.serving_size),
            "nutrition_source": bool(self.nutrition_source),
            "nutrition_reviewed": self.nutrition_reviewed,
        }
        if any(nutrition.values()) and not all(nutrition.values()):
            raise ValidationError({key: "Provide calories, serving size and source, and confirm the estimate together; or leave all nutrition fields empty."
                                   for key, present in nutrition.items() if not present})
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
                # A previous estimate must not silently follow a changed recipe.
                self.calories_kcal = None
                self.serving_size = ""
                self.nutrition_source = ""
                self.nutrition_reviewed = False
                if kwargs.get("update_fields") is not None:
                    kwargs["update_fields"] = set(kwargs["update_fields"]) | {
                        "ingredient_version", "ingredients_reviewed", "status", "dietary_tags",
                        "calories_kcal", "serving_size", "nutrition_source", "nutrition_reviewed"
                    }
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.dish} — {self.seller}"
