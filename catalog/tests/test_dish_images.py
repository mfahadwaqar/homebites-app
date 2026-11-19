from django.test import SimpleTestCase

from catalog.models import Dish, FoodListing


class DishImageTests(SimpleTestCase):
    def test_chicken_biryani_uses_biryani_image(self):
        dish = Dish(code="PK01", country_id="PK", name="Chicken Biryani")
        listing = FoodListing(dish=dish, dietary_tags=[])
        self.assertEqual(listing.illustrative_image, "catalog/food/real/PK01-chicken-biryani.jpg")

    def test_chicken_karahi_uses_separate_real_photograph(self):
        dish = Dish(code="PK04", country_id="PK", name="Chicken Karahi")
        self.assertEqual(dish.illustrative_image, "catalog/food/real/PK04-chicken-karahi.jpg")

    def test_photo_sources_match_catalogue_and_have_local_files_and_credits(self):
        from pathlib import Path
        from django.conf import settings
        from catalog.photos import reviewed_photos
        from catalog.manifest import dish_index
        for code, photo in reviewed_photos().items():
            self.assertEqual(dish_index()[code]["name"], photo["dish"])
            self.assertTrue((Path(settings.BASE_DIR) / "static" / photo["path"]).is_file())
            keys = ["author", "license", "modifications"] if photo.get("ai") else ["author", "source_url", "license", "license_url", "modifications"]
            for key in keys:
                self.assertTrue(photo[key])

    def test_seller_upload_takes_priority_over_catalogue_credit(self):
        listing = FoodListing(dish_id="PK01", image="seller-photo.jpg")
        self.assertIsNone(listing.catalogue_photo)

    def test_vegetarian_recipe_does_not_get_meat_photo_credit(self):
        dish = Dish(code="PK01", country_id="PK", name="Chicken Biryani")
        listing = FoodListing(dish=dish, dietary_tags=["vegetarian"])
        self.assertIsNone(listing.catalogue_photo)
        self.assertEqual(listing.illustrative_image, "catalog/food/pakistan-vegetarian.webp")


class PhotoDietTests(SimpleTestCase):
    def listing(self, code, tags):
        from catalog.manifest import dish_index
        row = dish_index()[code]
        return FoodListing(dish=Dish(code=code, country_id=row["country"], name=row["name"]), dietary_tags=tags)

    def test_all_fifty_dishes_have_a_real_photograph(self):
        from catalog.photos import reviewed_photos
        from catalog.manifest import dish_index
        self.assertEqual(set(reviewed_photos()), set(dish_index()))

    def test_meatless_photo_is_kept_for_vegetarian_and_vegan_offers(self):
        self.assertIsNotNone(self.listing("PK08", ["vegetarian", "vegan"]).catalogue_photo)
        self.assertIsNotNone(self.listing("IN04", ["vegetarian"]).catalogue_photo)

    def test_vegetarian_only_photo_is_not_used_for_vegan_offer(self):
        self.assertIsNone(self.listing("IN04", ["vegetarian", "vegan"]).catalogue_photo)

    def test_photo_without_diet_flag_is_not_used_for_vegetarian_offer(self):
        self.assertIsNone(self.listing("TH01", ["vegetarian"]).catalogue_photo)


    def test_halal_label_does_not_remove_the_photo(self):
        self.assertIsNotNone(self.listing("PK01", ["halal"]).catalogue_photo)
        self.assertIsNotNone(self.listing("PK08", ["vegetarian", "vegan", "halal"]).catalogue_photo)
        self.assertIsNone(self.listing("PK01", ["vegetarian", "halal"]).catalogue_photo)
