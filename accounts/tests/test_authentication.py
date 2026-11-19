from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="maya",
            email="maya@example.test",
            display_name="Maya Rahman",
            password="safe-test-password-2026",
        )

    def test_valid_login_redirects_to_explore_food(self):
        response = self.client.post(
            reverse("login"),
            {"username": "maya", "password": "safe-test-password-2026"},
        )

        self.assertRedirects(
            response,
            reverse("catalog:list"),
            fetch_redirect_response=False,
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_authenticated_user_is_not_switched_by_login_form(self):
        other_user = get_user_model().objects.create_user(
            username="other-user",
            password="other-safe-password-2026",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("login"),
            {"username": other_user.username, "password": "other-safe-password-2026"},
        )

        self.assertRedirects(
            response,
            reverse("catalog:list"),
            fetch_redirect_response=False,
        )
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_logout_rejects_get_and_accepts_post(self):
        self.client.force_login(self.user)

        get_response = self.client.get(reverse("logout"))
        post_response = self.client.post(reverse("logout"))

        self.assertEqual(get_response.status_code, 405)
        self.assertRedirects(post_response, reverse("home"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_password_reset_existing_email_sends_local_preview(self):
        response = self.client.post(
            reverse("password_reset"),
            {"email": "maya@example.test"},
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("HomeBites password reset", mail.outbox[0].subject)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)

    def test_password_reset_unknown_email_uses_same_response_without_email(self):
        response = self.client.post(
            reverse("password_reset"),
            {"email": "unknown@example.test"},
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

