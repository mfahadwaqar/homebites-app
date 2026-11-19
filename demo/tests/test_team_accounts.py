import json
import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.test import TestCase

from fulfillment.models import DemoLocation
from sellers.models import SellerProfile


class TeamAccountsTests(TestCase):
    def setUp(self):
        DemoLocation.objects.create(code="T1", label="Ari", city="Bangkok", latitude="13.78", longitude="100.54", is_active=True)

    def run_command(self, rows):
        with mock.patch.dict(os.environ, {"TEAM_ACCOUNTS": json.dumps(rows)}):
            call_command("create_team_accounts")

    def test_creates_buyer_approved_seller_and_staff_admin_with_given_passwords(self):
        rows = [
            {"username": "b1", "email": "b@example.com", "display_name": "Buyer", "role": "buyer", "password_hash": make_password("pw-buyer-1")},
            {"username": "s1", "email": "s@example.com", "display_name": "Seller", "role": "seller", "storefront_name": "Kitchen One", "password_hash": make_password("pw-seller-1")},
            {"username": "a1", "email": "a@example.com", "display_name": "Admin", "role": "admin", "password_hash": make_password("pw-admin-1")},
        ]
        self.run_command(rows)
        self.run_command(rows)  # safe to repeat
        users = get_user_model().objects
        self.assertTrue(users.get(username="b1").check_password("pw-buyer-1"))
        self.assertFalse(users.get(username="b1").is_staff)
        seller = SellerProfile.objects.get(user__username="s1")
        self.assertEqual(seller.status, SellerProfile.Status.APPROVED)
        self.assertEqual(seller.storefront_name, "Kitchen One")
        self.assertIsNotNone(seller.pickup_location)
        admin = users.get(username="a1")
        self.assertTrue(admin.is_staff and admin.is_superuser)
        self.assertEqual(users.filter(username__in=["b1", "s1", "a1"]).count(), 3)

    def test_does_nothing_without_the_environment_variable(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEAM_ACCOUNTS", None)
            call_command("create_team_accounts")
        self.assertFalse(get_user_model().objects.filter(username="b1").exists())
