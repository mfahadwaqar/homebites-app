"""Release overdue fake-payment inventory holds in a local demo database."""

from django.core.management.base import BaseCommand

from orders.services.checkout import expire_reservations


class Command(BaseCommand):
    help = "Expire overdue simulated payment holds and release their portions. Safe to rerun."

    def handle(self, *args, **options):
        count = expire_reservations()
        self.stdout.write(f"Expired {count} overdue simulated payment hold(s).")
