from django.core.management import call_command
from django.core.management.base import BaseCommand

from catalog.models import Dish


class Command(BaseCommand):
    help = "Prepare a hosted demo: seed once on an empty database, then set demo logins."

    def handle(self, *args, **options):
        if Dish.objects.exists():
            self.stdout.write("Catalogue already seeded; leaving existing data alone.")
        else:
            call_command("seed_catalogue")
            call_command("seed_demo")
            call_command("seed_sample_reviews")
        call_command("set_demo_passwords")
        call_command("create_team_accounts")
