from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelTests(TestCase):
    def test_project_uses_homebites_user_model(self):
        user_model = get_user_model()

        self.assertEqual(user_model._meta.label, "accounts.User")

    def test_display_name_persists(self):
        user_model = get_user_model()

        user = user_model.objects.create_user(
            username="maya",
            password="safe-test-password-2026",
            display_name="Maya Rahman",
        )

        self.assertEqual(user_model.objects.get(pk=user.pk).display_name, "Maya Rahman")

    def test_user_is_registered_with_admin(self):
        user_model = get_user_model()

        self.assertIn(user_model, admin.site._registry)

