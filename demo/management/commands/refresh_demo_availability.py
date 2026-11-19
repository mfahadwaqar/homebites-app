from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from demo.services import refresh_demo_availability


class Command(BaseCommand):
    help = "Refresh expired marked demo schedules, preserving current stock, pauses and history."

    def handle(self, *args, **options):
        summary = refresh_demo_availability(at=timezone.now())
        self.stdout.write(str(summary))
        if summary.problems:
            raise CommandError(" ".join(summary.problems))
