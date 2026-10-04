from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from catalog.models import FoodListing


class CartServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from orders.models import FulfillmentSlot, ListingStock

        call_command("seed_catalogue", verbosity=0)
        cls.buyer = get_user_model().objects.create_user(
            username="cart-buyer", password="safe-test-password-2026",
        )
        cls.first_listing = FoodListing.objects.public().order_by("pk").first()
        cls.other_listing = FoodListing.objects.public().exclude(
            seller=cls.first_listing.seller,
        ).order_by("pk").first()
        start = timezone.now() + timedelta(hours=2)
        cls.first_slot = FulfillmentSlot.objects.create(
            seller=cls.first_listing.seller,
            order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start,
            ends_at=start + timedelta(hours=2),
            allows_pickup=True,
            allows_delivery=True,
        )
        cls.other_slot = FulfillmentSlot.objects.create(
            seller=cls.other_listing.seller,
            order_type=FulfillmentSlot.OrderType.STANDARD,
            starts_at=start,
            ends_at=start + timedelta(hours=2),
            allows_pickup=True,
            allows_delivery=True,
        )
        ListingStock.objects.create(
            listing=cls.first_listing, slot=cls.first_slot, capacity=3,
        )
        ListingStock.objects.create(
            listing=cls.other_listing, slot=cls.other_slot, capacity=3,
        )

    def test_conflicting_seller_does_not_discard_existing_cart(self):
        from orders.models import CartItem
        from orders.services.cart import CartConflict, add_to_cart

        cart = add_to_cart(self.buyer, self.first_listing, self.first_slot, 1)

        with self.assertRaises(CartConflict):
            add_to_cart(self.buyer, self.other_listing, self.other_slot, 1)

        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 1)
        self.assertEqual(cart.items.get().listing_id, self.first_listing.pk)

    def test_buyer_cannot_add_their_own_listing(self):
        from orders.services.cart import CartError, add_to_cart

        with self.assertRaises(CartError):
            add_to_cart(
                self.first_listing.seller.user,
                self.first_listing,
                self.first_slot,
                1,
            )

    def test_cart_does_not_reserve_stock(self):
        from orders.models import ListingStock
        from orders.services.cart import add_to_cart

        add_to_cart(self.buyer, self.first_listing, self.first_slot, 2)
        stock = ListingStock.objects.get(
            listing=self.first_listing,
            slot=self.first_slot,
        )

        self.assertEqual(stock.held, 0)
        self.assertEqual(stock.committed, 0)

