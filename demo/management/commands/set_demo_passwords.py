import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Set demo logins from the DEMO_PASSWORD environment variable (for a hosted demo)."

    def handle(self, *args, **options):
        password = os.environ.get("DEMO_PASSWORD", "").strip()
        if not password:
            self.stdout.write("DEMO_PASSWORD is not set; no passwords changed.")
            return
        user_model = get_user_model()
        changed = []
        for user in user_model.objects.filter(username__startswith="demo_").exclude(username="demo_admin"):
            user.set_password(password)
            user.save(update_fields=["password"])
            changed.append(user.username)
        admin, _ = user_model.objects.get_or_create(username="demo_admin", defaults={"display_name": "Demo Admin"})
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.set_password(password)
        admin.save()
        changed.append("demo_admin")
        self.stdout.write("Demo passwords set for: " + ", ".join(changed))
