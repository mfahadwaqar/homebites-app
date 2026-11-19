from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class SignUpTests(TestCase):
    def test_signup_page_is_available(self):
        response = self.client.get(reverse("accounts:signup"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your HomeBites account")

    def test_valid_signup_creates_user_signs_them_in_and_shows_their_name(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "maya",
                "email": "maya@example.test",
                "display_name": "Maya Rahman",
                "password1": "safe-test-password-2026",
                "password2": "safe-test-password-2026",
            },
        )

        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertIn("_auth_user_id", self.client.session)
        page = self.client.get(reverse("home"))
        self.assertContains(page, "Welcome to HomeBites, maya")
        self.assertContains(page, "Signed in as maya")
        user = get_user_model().objects.get(username="maya")
        self.assertEqual(user.email, "maya@example.test")
        self.assertEqual(user.display_name, "Maya Rahman")

    def test_duplicate_username_does_not_create_another_user(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="maya",
            password="safe-test-password-2026",
        )

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "maya",
                "email": "other@example.test",
                "display_name": "Other Maya",
                "password1": "another-safe-password-2026",
                "password2": "another-safe-password-2026",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with that username already exists")
        self.assertEqual(user_model.objects.filter(username="maya").count(), 1)

    def test_authenticated_user_cannot_create_another_account(self):
        user_model = get_user_model()
        current_user = user_model.objects.create_user(
            username="maya",
            password="safe-test-password-2026",
        )
        self.client.force_login(current_user)

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "second-account",
                "email": "second@example.test",
                "display_name": "Second Account",
                "password1": "another-safe-password-2026",
                "password2": "another-safe-password-2026",
            },
        )

        self.assertRedirects(
            response,
            reverse("catalog:list"),
            fetch_redirect_response=False,
        )
        self.assertEqual(user_model.objects.count(), 1)

