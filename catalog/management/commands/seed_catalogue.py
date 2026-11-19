import json
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.manifest import load_manifest
from catalog.models import COUNTRIES, Country, Dish, FoodListing, category_for
from sellers.models import SellerProfile


DEMO_STOREFRONTS = {
    "TH": "Thai Home Kitchen",
    "PK": "Pakistani Home Kitchen",
    "BD": "Bangladeshi Home Kitchen",
    "NP": "Nepali Home Kitchen",
    "IN": "Indian Home Kitchen",
}

# These labels describe only the fictional seller recipes in the manifest,
# never a universal recipe or an allergy/certification guarantee.
VEGAN_DEMO_CODES = {"TH10", "PK08", "BD07", "NP05", "IN05"}
VEGETARIAN_DEMO_CODES = {"TH01", "PK10", "BD02", "NP02", "IN04"}
# Fictional seller declaration: every Pakistani and Bangladeshi demo kitchen is halal,
# plus a few Nepali and Indian dishes so both options exist. Not a certification.
HALAL_DEMO_CODES = {"NP01", "NP04", "NP09", "IN01", "IN06", "IN09"}


def _demo_tags(row):
    tags = (["vegetarian", "vegan"] if row["code"] in VEGAN_DEMO_CODES
            else ["vegetarian"] if row["code"] in VEGETARIAN_DEMO_CODES else [])
    if row["country"] in ("PK", "BD") or row["code"] in HALAL_DEMO_CODES:
        tags.append("halal")
    return tags


def _nutrition():
    path = Path(__file__).resolve().parents[2] / "data" / "nutrition.json"
    return json.loads(path.read_text(encoding="utf-8"))


class Command(BaseCommand):
    help = "Seed the fixed five-country catalogue and 50 reviewed demo seller offers."

    @transaction.atomic
    def handle(self, *args, **options):
        nutrition = _nutrition()
        rows = load_manifest()
        countries = {}
        sellers = {}
        for code, name in COUNTRIES.items():
            country, _ = Country.objects.get_or_create(code=code, defaults={"name": name})
            countries[code] = country

            username = f"demo_seller_{name.lower()}"
            user, created = get_user_model().objects.get_or_create(username=username)
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            elif user.has_usable_password():
                raise CommandError(f"Refusing to approve existing account {username!r} as a demo seller.")
            seller, _ = SellerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "storefront_name": DEMO_STOREFRONTS[code],
                    "description": f"Fictional Bangkok home kitchen offering {name} dishes.",
                    "status": SellerProfile.Status.APPROVED,
                },
            )
            sellers[code] = seller

        for row in rows:
            dish, created = Dish.objects.get_or_create(
                code=row["code"],
                defaults={
                    "country": countries[row["country"]],
                    "name": row["name"],
                    "description": row["description"],
                    "default_ingredients": row["ingredients"],
                    "category": category_for(row["code"]),
                },
            )
            if not created:
                # Master defaults may be refreshed; seller recipes stay independent.
                dish.description = row["description"]
                dish.default_ingredients = row["ingredients"]
                dish.category = category_for(row["code"])
                dish.save(update_fields=["description", "default_ingredients", "category"])
            info = nutrition[row["code"]]
            nutrition_fields = {
                "calories_kcal": info["calories_kcal"], "serving_size": info["serving_size"],
                "nutrition_source": info["source"], "nutrition_reviewed": True,
            }
            listing, listing_created = FoodListing.objects.get_or_create(
                seller=sellers[row["country"]],
                dish=dish,
                defaults={
                    "description": f"{row['description']} Prepared by {DEMO_STOREFRONTS[row['country']] }.",
                    "price": Decimal(row["price"]),
                    "ingredients": list(row["ingredients"]),
                    "dietary_tags": _demo_tags(row),
                    "ingredients_reviewed": True,
                    "status": FoodListing.Status.PUBLISHED,
                    **nutrition_fields,
                },
            )
            # Add the halal declaration to existing demo offers without touching other tags.
            if not listing_created and "halal" in _demo_tags(row) and "halal" not in listing.dietary_tags:
                listing.dietary_tags = [*listing.dietary_tags, "halal"]
                listing.save(update_fields=["dietary_tags"])
            # Fill a missing estimate only while the seller recipe still matches the
            # reviewed reference recipe; never overwrite seller-entered values.
            if not listing_created and not listing.has_nutrition and listing.ingredients == list(row["ingredients"]):
                for field, value in nutrition_fields.items():
                    setattr(listing, field, value)
                listing.save(update_fields=list(nutrition_fields))
        self.stdout.write(self.style.SUCCESS("Seeded 5 countries, 50 dishes and 50 reviewed demo offers."))
