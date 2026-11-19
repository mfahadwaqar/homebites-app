import json
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from fulfillment.models import DemoLocation
from sellers.models import SellerProfile


class Command(BaseCommand):
    help = (
        "Create real-person accounts from the TEAM_ACCOUNTS environment variable "
        "(a JSON list of username, email, display_name, role, password_hash, storefront_name)."
    )

    def handle(self, *args, **options):
        raw = os.environ.get("TEAM_ACCOUNTS", "").strip()
        if not raw:
            self.stdout.write("TEAM_ACCOUNTS is not set; no team accounts created.")
            return
        user_model = get_user_model()
        done = []
        for row in json.loads(raw):
            user, _ = user_model.objects.get_or_create(username=row["username"])
            user.email = row.get("email", "")
            user.display_name = row.get("display_name", "")
            user.is_active = True
            role = row.get("role", "buyer")
            user.is_staff = role == "admin"
            user.is_superuser = role == "admin"
            if row.get("password_hash"):
                user.password = row["password_hash"]
            user.save()
            if role == "seller":
                location = DemoLocation.objects.filter(is_active=True, city__iexact="bangkok").order_by("label").first()
                SellerProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        "storefront_name": row.get("storefront_name") or row.get("display_name") or user.username,
                        "description": row.get("description", ""),
                        "pickup_location": location,
                        "status": SellerProfile.Status.APPROVED,
                    },
                )
            done.append(f"{user.username} ({role})")
        self.stdout.write("Team accounts ready: " + ", ".join(done))
