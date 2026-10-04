from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


class LocalLoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        get_user_model().objects.create_user(username="demo-buyer", password="correct-demo-password")

    def tearDown(self):
        cache.clear()

    def test_sixth_attempt_is_rate_limited_even_if_password_is_correct(self):
        for _ in range(5):
            response = self.client.post(
                reverse("login"), {"username": "demo-buyer", "password": "wrong"},
                REMOTE_ADDR="192.0.2.20",
            )
            self.assertEqual(response.status_code, 200)

        blocked = self.client.post(
            reverse("login"), {"username": "demo-buyer", "password": "correct-demo-password"},
            REMOTE_ADDR="192.0.2.20",
        )
        self.assertEqual(blocked.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_success_clears_failed_attempts_and_other_source_is_not_blocked(self):
        for _ in range(4):
            self.client.post(
                reverse("login"), {"username": "demo-buyer", "password": "wrong"},
                REMOTE_ADDR="192.0.2.21",
            )
        valid = self.client.post(
            reverse("login"), {"username": "demo-buyer", "password": "correct-demo-password"},
            REMOTE_ADDR="192.0.2.21",
        )
        self.assertEqual(valid.status_code, 302)
        self.client.logout()
        for _ in range(4):
            response = self.client.post(
                reverse("login"), {"username": "demo-buyer", "password": "wrong"},
                REMOTE_ADDR="192.0.2.21",
            )
            self.assertEqual(response.status_code, 200)
        other_source = self.client.post(
            reverse("login"), {"username": "demo-buyer", "password": "correct-demo-password"},
            REMOTE_ADDR="192.0.2.22",
        )
        self.assertEqual(other_source.status_code, 302)
