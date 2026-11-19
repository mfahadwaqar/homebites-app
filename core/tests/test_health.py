from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command


class HomePageTests(TestCase):
    def test_home_page_identifies_the_marketplace_and_discloses_simulation(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HomeBites")
        self.assertContains(response, "A taste of home")
        self.assertContains(response, "HomeBites is a university project")
        self.assertContains(response, "are simulated")

    def test_home_page_links_to_five_cuisines_and_public_offers(self):
        call_command("seed_catalogue", verbosity=0)
        response = self.client.get(reverse("home"))

        for code in ("TH", "PK", "BD", "NP", "IN"):
            self.assertContains(response, f"country={code}")
        self.assertContains(response, "Pad Thai")
        self.assertContains(response, "AI-generated illustration")

    def test_home_page_declares_local_favicon(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'rel="icon"')
        self.assertContains(response, '/static/images/homebites-mark.svg')

    def test_browser_default_favicon_resolves_to_the_local_mark(self):
        response = self.client.get('/favicon.ico')
        self.assertRedirects(response, '/static/images/homebites-mark.svg', fetch_redirect_response=False)

