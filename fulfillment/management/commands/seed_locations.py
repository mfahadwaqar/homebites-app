"""Seed stable fictional sample points around Bangkok."""

from django.core.management.base import BaseCommand
from django.db import transaction

from fulfillment.models import DeliveryTariff, DemoLocation


LOCATIONS = (
    ("ari", "Ari", "13.779700", "100.544800"),
    ("asok", "Asok", "13.737900", "100.560200"),
    ("bang-na", "Bang Na", "13.668000", "100.604500"),
    ("chatuchak", "Chatuchak", "13.799900", "100.550200"),
    ("lat-phrao", "Lat Phrao", "13.816000", "100.606000"),
    ("siam", "Siam", "13.746800", "100.534900"),
    ("silom", "Silom", "13.728500", "100.535000"),
    ("thonglor", "Thonglor", "13.730700", "100.585400"),
)


class Command(BaseCommand):
    help = "Seed offline Bangkok sample locations and version 1 demo tariff."

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        for code, label, latitude, longitude in LOCATIONS:
            _, created = DemoLocation.objects.get_or_create(
                code=code,
                defaults={
                    "label": label,
                    "city": "Bangkok",
                    "latitude": latitude,
                    "longitude": longitude,
                },
            )
            created_count += created
        DeliveryTariff.objects.get_or_create(version=1)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created_count} new Bangkok demo locations; {len(LOCATIONS)} known locations."
        ))
