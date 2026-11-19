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

    def test_cart_holds_dishes_from_several_kitchens(self):
        from orders.models import CartItem
        from orders.services.cart import add_to_cart, cart_groups

        cart = add_to_cart(self.buyer, self.first_listing, self.first_slot, 1)
        add_to_cart(self.buyer, self.other_listing, self.other_slot, 2)

        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 2)
        groups = cart_groups(cart)
        self.assertEqual(len(groups), 2)
        self.assertEqual({g.seller.pk for g in groups}, {self.first_listing.seller_id, self.other_listing.seller_id})

    def test_same_dish_cannot_be_in_cart_for_two_windows(self):
        from orders.services.cart import CartError, add_to_cart

        add_to_cart(self.buyer, self.first_listing, self.first_slot, 1)
        from datetime import timedelta
        from django.utils import timezone
        from orders.models import FulfillmentSlot, ListingStock
        start = timezone.now() + timedelta(hours=5)
        second = FulfillmentSlot.objects.create(seller=self.first_listing.seller, order_type="standard", starts_at=start, ends_at=start + timedelta(hours=2))
        ListingStock.objects.create(listing=self.first_listing, slot=second, capacity=3)
        with self.assertRaises(CartError):
            add_to_cart(self.buyer, self.first_listing, second, 1)

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

