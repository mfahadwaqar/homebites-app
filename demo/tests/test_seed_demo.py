from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from catalog.models import Country, Dish, FoodListing
from demo.models import DemoBuyer, DemoSlot
from fulfillment.models import DemoLocation
from orders.models import FulfillmentSlot, ListingStock
from sellers.models import SellerProfile


class SeedDemoTests(TestCase):
    def test_seed_builds_five_bangkok_kitchens_and_two_live_slots_per_offer(self):
        call_command("seed_demo", verbosity=0)

        self.assertEqual(Country.objects.count(), 5)
        self.assertEqual(Dish.objects.count(), 50)
        self.assertEqual(FoodListing.objects.public().count(), 50)
        self.assertEqual(DemoLocation.objects.count(), 8)
        sellers = SellerProfile.objects.filter(user__username__startswith="demo_seller_")
        self.assertEqual(sellers.count(), 5)
        self.assertEqual(len(set(sellers.values_list("pickup_location_id", flat=True))), 5)
        self.assertTrue(all(seller.pickup_location.city == "Bangkok" for seller in sellers))
        self.assertEqual(DemoSlot.objects.count(), 10)
        self.assertEqual(FulfillmentSlot.objects.count(), 10)
        self.assertEqual(ListingStock.objects.count(), 100)
        self.assertTrue(all(stock.available > 0 for stock in ListingStock.objects.all()))
        self.assertTrue(all(listing.stocks.count() == 2 for listing in FoodListing.objects.public()))
        self.assertTrue(all(slot.ends_at > timezone.now() for slot in FulfillmentSlot.objects.all()))
        self.assertTrue(all(
            slot.preorder_deadline and timezone.now() < slot.preorder_deadline < slot.starts_at
            for slot in FulfillmentSlot.objects.filter(order_type=FulfillmentSlot.OrderType.PREORDER)
        ))

    def test_repeat_preserves_slot_ids_and_used_stock(self):
        call_command("seed_demo", verbosity=0)
        stock = ListingStock.objects.order_by("pk").first()
        stock.held = 2
        stock.save(update_fields=["held"])
        slot_ids = set(DemoSlot.objects.values_list("slot_id", flat=True))

        call_command("seed_demo", verbosity=0)

        stock.refresh_from_db()
        self.assertEqual(stock.held, 2)
        self.assertEqual(set(DemoSlot.objects.values_list("slot_id", flat=True)), slot_ids)
        self.assertEqual(FulfillmentSlot.objects.count(), 10)
        self.assertEqual(ListingStock.objects.count(), 100)
        self.assertEqual(FoodListing.objects.count(), 50)

    def test_buyer_is_guarded_and_password_can_be_set_without_seed_overwriting_it(self):
        call_command("seed_demo", verbosity=0)
        buyer = get_user_model().objects.get(username="demo_buyer")
        self.assertEqual(DemoBuyer.objects.get().user_id, buyer.pk)
        self.assertFalse(buyer.has_usable_password())
        self.assertTrue(buyer.is_active)
        self.assertFalse(buyer.is_staff)
        buyer.set_password("local-only-test-password")
        buyer.save(update_fields=["password"])

        call_command("seed_demo", verbosity=0)

        buyer.refresh_from_db()
        self.assertTrue(buyer.check_password("local-only-test-password"))
        self.assertEqual(DemoBuyer.objects.count(), 1)

    def test_existing_unmarked_buyer_username_is_not_adopted(self):
        get_user_model().objects.create_user(username="demo_buyer", password="existing-private-password")
        with self.assertRaises(CommandError):
            call_command("seed_demo", verbosity=0)
        self.assertEqual(DemoBuyer.objects.count(), 0)
        self.assertEqual(Country.objects.count(), 0)

    def test_expired_demo_slot_rotates_without_rewriting_old_stock(self):
        call_command("seed_demo", verbosity=0)
        marker = DemoSlot.objects.filter(order_type=FulfillmentSlot.OrderType.STANDARD).first()
        old_slot_id = marker.slot_id
        FulfillmentSlot.objects.filter(pk=old_slot_id).update(
            starts_at=timezone.now() - timedelta(days=2),
            ends_at=timezone.now() - timedelta(days=1),
        )

        call_command("seed_demo", verbosity=0)

        marker.refresh_from_db()
        self.assertNotEqual(marker.slot_id, old_slot_id)
        self.assertFalse(FulfillmentSlot.objects.get(pk=old_slot_id).is_active)
        self.assertEqual(ListingStock.objects.filter(slot_id=old_slot_id).count(), 10)
        self.assertEqual(ListingStock.objects.filter(slot=marker.slot).count(), 10)
        self.assertEqual(DemoSlot.objects.count(), 10)
        self.assertEqual(FulfillmentSlot.objects.filter(is_active=True).count(), 10)
