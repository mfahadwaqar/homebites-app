from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.manifest import load_manifest
from catalog.models import COUNTRIES, Country, Dish, FoodListing
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


class Command(BaseCommand):
    help = "Seed the fixed five-country catalogue and 50 reviewed demo seller offers."

    @transaction.atomic
    def handle(self, *args, **options):
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
                },
            )
            if not created:
                # Master defaults may be refreshed; seller recipes stay independent.
                dish.description = row["description"]
                dish.default_ingredients = row["ingredients"]
                dish.save(update_fields=["description", "default_ingredients"])
            FoodListing.objects.get_or_create(
                seller=sellers[row["country"]],
                dish=dish,
                defaults={
                    "description": f"{row['description']} Prepared by {DEMO_STOREFRONTS[row['country']] }.",
                    "price": Decimal(row["price"]),
                    "ingredients": list(row["ingredients"]),
                    "dietary_tags": (["vegetarian", "vegan"] if row["code"] in VEGAN_DEMO_CODES
                                     else ["vegetarian"] if row["code"] in VEGETARIAN_DEMO_CODES else []),
                    "ingredients_reviewed": True,
                    "status": FoodListing.Status.PUBLISHED,
                },
            )
        self.stdout.write(self.style.SUCCESS("Seeded 5 countries, 50 dishes and 50 reviewed demo offers."))
