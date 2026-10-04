from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.manifest import load_manifest
from catalog.models import Country, Dish, FoodListing
from sellers.models import SellerProfile
from orders.models import FulfillmentSlot, ListingStock


class DiscoveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(username="discovery_seller", password="test-password")
        cls.seller = SellerProfile.objects.create(
            user=user, storefront_name="Bangkok Family Kitchen", status=SellerProfile.Status.APPROVED,
        )
        second_user = get_user_model().objects.create_user(username="second_seller", password="test-password")
        cls.second_seller = SellerProfile.objects.create(
            user=second_user, storefront_name="Second Kitchen", status=SellerProfile.Status.APPROVED,
        )
        countries = {}
        cls.listings = []
        for row in load_manifest()[:13]:
            country = countries.setdefault(
                row["country"],
                Country.objects.get_or_create(
                    code=row["country"],
                    defaults={"name": {"TH": "Thailand", "PK": "Pakistan"}[row["country"]]},
                )[0],
            )
            dish = Dish.objects.create(
                code=row["code"], country=country, name=row["name"],
                description=row["description"], default_ingredients=row["ingredients"],
            )
            cls.listings.append(FoodListing.objects.create(
                seller=cls.seller, dish=dish, price=Decimal(row["price"]),
                ingredients=row["ingredients"], ingredients_reviewed=True,
                status=FoodListing.Status.PUBLISHED,
            ))
        cls.pad_thai = cls.listings[0]
        cls.second_pad_thai = FoodListing.objects.create(
            seller=cls.second_seller, dish=cls.pad_thai.dish, price=Decimal("180.00"),
            ingredients=["rice noodles", "tofu", "sesame"], ingredients_reviewed=True,
            status=FoodListing.Status.PUBLISHED,
        )
        cls.hidden = cls.listings[-1]
        FoodListing.objects.filter(pk=cls.hidden.pk).update(status=FoodListing.Status.DRAFT)

    def test_list_excludes_unpublished_offers_and_shows_seller_links(self):
        response = self.client.get(reverse("catalog:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 13)
        self.assertContains(response, "Bangkok Family Kitchen")
        self.assertContains(response, reverse("sellers:storefront", args=[self.seller.pk]))
        self.assertNotContains(response, reverse("catalog:detail", args=[self.hidden.pk]))

    def test_search_matches_dish_description_and_seller_name(self):
        for query, expected in (("Pad Thai", 2), ("rice noodles", 2), ("Second Kitchen", 1)):
            with self.subTest(query=query):
                response = self.client.get(reverse("catalog:list"), {"q": query})
                self.assertEqual(response.context["page_obj"].paginator.count, expected)

    def test_country_and_price_filters_combine(self):
        response = self.client.get(reverse("catalog:list"), {
            "country": "TH", "min_price": "100", "max_price": "130",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 5)
        self.assertContains(response, "Pad Thai")
        self.assertNotContains(response, "Chicken Biryani")

    def test_seller_declared_vegetarian_filter_excludes_unlabelled_offers(self):
        self.second_pad_thai.dietary_tags = ["vegetarian"]
        self.second_pad_thai.save(update_fields=["dietary_tags"])
        response = self.client.get(reverse("catalog:list"), {"dietary": "vegetarian"})
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "Second Kitchen")
        self.assertNotContains(response, "Bangkok Family Kitchen")

    def test_invalid_price_does_not_crash_listing(self):
        response = self.client.get(reverse("catalog:list"), {"min_price": "bad", "max_price": "-5"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 13)

    def test_pagination_preserves_search_filter(self):
        response = self.client.get(reverse("catalog:list"), {"country": "TH"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 11)
        self.assertContains(response, "country=TH&amp;page=2")
        second = self.client.get(reverse("catalog:list"), {"country": "TH", "page": "2"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.context["page_obj"].number, 2)

    def test_detail_displays_this_sellers_ingredients_and_link(self):
        response = self.client.get(reverse("catalog:detail", args=[self.second_pad_thai.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tofu")
        self.assertContains(response, "sesame")
        self.assertNotContains(response, "bean sprouts")
        self.assertContains(response, reverse("sellers:storefront", args=[self.second_seller.pk]))

    def test_detail_returns_404_for_unpublished_offer(self):
        response = self.client.get(reverse("catalog:detail", args=[self.hidden.pk]))
        self.assertEqual(response.status_code, 404)

    def test_seller_image_appears_on_card_and_detail(self):
        FoodListing.objects.filter(pk=self.pad_thai.pk).update(image="listing_images/pad-thai.jpg")
        card = self.client.get(reverse("catalog:list"))
        detail = self.client.get(reverse("catalog:detail", args=[self.pad_thai.pk]))
        self.assertContains(card, "listing_images/pad-thai.jpg")
        self.assertContains(detail, "listing_images/pad-thai.jpg")

    def test_availability_requires_open_slot_with_remaining_portions(self):
        start = timezone.now() + timedelta(hours=2)
        slot = FulfillmentSlot.objects.create(
            seller=self.seller, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start, ends_at=start + timedelta(hours=2),
        )
        ListingStock.objects.create(listing=self.pad_thai, slot=slot, capacity=2, held=1)
        ListingStock.objects.create(listing=self.listings[1], slot=slot, capacity=1, committed=1)
        inactive_slot = FulfillmentSlot.objects.create(
            seller=self.seller, order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start, ends_at=start + timedelta(hours=2), is_active=False,
        )
        ListingStock.objects.create(listing=self.listings[2], slot=inactive_slot, capacity=2)

        response = self.client.get(reverse("catalog:list"), {"available": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, reverse("catalog:detail", args=[self.pad_thai.pk]))

    def test_availability_excludes_expired_preorder_deadline(self):
        start = timezone.now() + timedelta(days=2)
        slot = FulfillmentSlot.objects.create(
            seller=self.seller, order_type=FulfillmentSlot.OrderType.PREORDER,
            starts_at=start, ends_at=start + timedelta(hours=2),
            preorder_deadline=timezone.now() - timedelta(minutes=1),
        )
        ListingStock.objects.create(listing=self.pad_thai, slot=slot, capacity=2)

        response = self.client.get(reverse("catalog:list"), {"available": "1"})
        self.assertEqual(response.context["page_obj"].paginator.count, 0)


class SeededDiscoveryTests(TestCase):
    def test_all_fifty_seeded_offers_are_browsable(self):
        call_command("seed_catalogue", verbosity=0)
        response = self.client.get(reverse("catalog:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 50)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 5)

        pakistan = self.client.get(reverse("catalog:list"), {"country": "PK"})
        self.assertEqual(pakistan.context["page_obj"].paginator.count, 10)
