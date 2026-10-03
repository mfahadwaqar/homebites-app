from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_home_page_identifies_simulated_marketplace(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HomeBites")
        self.assertContains(response, "university demonstration")
        self.assertContains(response, "Foundation milestone complete.")

    def test_home_page_declares_local_favicon(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'rel="icon"')
        self.assertContains(response, '/static/images/homebites-mark.svg')

