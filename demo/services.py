"""Explicit lifecycle of marked demonstration schedules; never called by public GETs."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from demo.models import DemoSlot
from orders.availability import booking_cutoff
from orders.models import FulfillmentSlot, ListingStock


@dataclass(frozen=True)
class RefreshSummary:
    created: int = 0
    retained: int = 0
    paused: int = 0
    problems: tuple = ()

    def __str__(self):
        return f"Demo windows: {self.created} refreshed, {self.retained} retained, {self.paused} paused."


def demo_slot_times(order_type, at):
    if order_type == "standard":
        start = at + timedelta(minutes=30)
        return start, start + timedelta(hours=2), None
    day = timezone.localdate(at) + timedelta(days=2)
    start = timezone.make_aware(datetime.combine(day, time(18)))
    return start, start + timedelta(hours=2), start - timedelta(days=1)


@transaction.atomic
def refresh_demo_availability(*, at):
    created = retained = paused = 0
    problems = []
    markers = list(DemoSlot.objects.select_for_update().order_by("pk"))
    if len(markers) != 10:
        problems.append("Expected ten marked demo windows. Run seed_demo to prepare the initial demo.")
    for marker in markers:
        slot = FulfillmentSlot.objects.select_for_update().get(pk=marker.slot_id)
        if slot.seller_id != marker.seller_id or slot.order_type != marker.order_type:
            problems.append(f"Demo window {marker.pk} has inconsistent ownership; staff review is required.")
            continue
        source = list(slot.stocks.select_related("listing").order_by("listing_id"))
        if len(source) != 10 or any(stock.listing.seller_id != marker.seller_id for stock in source):
            problems.append(f"Demo window {marker.pk} needs ten original stock associations; no stock was adopted.")
            continue
        if not slot.is_active:
            paused += 1
            continue
        cutoff = booking_cutoff(slot)
        if cutoff is not None and cutoff > at and slot.ends_at > at:
            retained += 1
            continue
        start, end, deadline = demo_slot_times(marker.order_type, at)
        replacement = FulfillmentSlot.objects.create(
            seller_id=marker.seller_id, order_type=marker.order_type,
            starts_at=start, ends_at=end, preorder_deadline=deadline,
            allows_pickup=slot.allows_pickup, allows_delivery=slot.allows_delivery,
        )
        for stock in source:
            ListingStock.objects.create(listing_id=stock.listing_id, slot=replacement, capacity=stock.capacity)
        slot.is_active = False
        slot.save(update_fields=["is_active"])
        marker.slot = replacement
        marker.save(update_fields=["slot"])
        created += 1
    return RefreshSummary(created, retained, paused, tuple(problems))
