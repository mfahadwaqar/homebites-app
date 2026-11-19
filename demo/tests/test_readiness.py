from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from demo.models import DemoSlot
from orders.models import FulfillmentSlot, ListingStock


class ReadinessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)
        cls.staff = get_user_model().objects.create_user(username="readiness-staff", is_staff=True)
        cls.buyer = get_user_model().objects.create_user(username="readiness-buyer")

    def test_only_staff_can_view_and_get_does_not_refresh(self):
        url = reverse("demo:readiness")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.staff)
        ids = set(DemoSlot.objects.values_list("slot_id", flat=True))
        response = self.client.get(url)
        self.assertContains(response, "Demo readiness")
        self.assertEqual(ids, set(DemoSlot.objects.values_list("slot_id", flat=True)))

    def test_refresh_requires_csrf_and_preserves_intentional_pause(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        slot = DemoSlot.objects.first().slot
        slot.is_active = False
        slot.save()
        url = reverse("demo:refresh")
        self.assertEqual(client.post(url).status_code, 403)
        client.get(reverse("demo:readiness"))
        response = client.post(url, {"csrfmiddlewaretoken": client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 302)
        slot.refresh_from_db()
        self.assertFalse(slot.is_active)
        self.assertEqual(FulfillmentSlot.objects.count(), 10)
        self.assertEqual(ListingStock.objects.count(), 100)
