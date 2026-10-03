from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ProfileTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("accounts:profile"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('accounts:profile')}",
            fetch_redirect_response=False,
        )

    def test_authenticated_user_can_view_profile(self):
        user = get_user_model().objects.create_user(
            username="maya",
            display_name="Maya Rahman",
            password="safe-test-password-2026",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Maya Rahman")

