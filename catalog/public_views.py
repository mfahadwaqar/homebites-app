from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Exists, F, OuterRef, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from catalog.models import Country, DIETARY_TAGS, FoodListing
from orders.models import FulfillmentSlot, ListingStock


def _nonnegative_price(value):
    try:
        price = Decimal(value)
    except (InvalidOperation, TypeError):
        return None
    return price if price.is_finite() and price >= 0 else None


def listing_list(request):
    listings = FoodListing.objects.public().select_related("dish", "dish__country", "seller")
    query = request.GET.get("q", "").strip()
    country = request.GET.get("country", "").strip().upper()
    dietary = request.GET.get("dietary", "").strip().lower()
    min_price = _nonnegative_price(request.GET.get("min_price"))
    max_price = _nonnegative_price(request.GET.get("max_price"))

    if query:
        listings = listings.filter(
            Q(dish__name__icontains=query)
            | Q(dish__description__icontains=query)
            | Q(description__icontains=query)
            | Q(seller__storefront_name__icontains=query)
        )
    if country:
        listings = listings.filter(dish__country_id=country)
    if dietary in DIETARY_TAGS:
        listings = listings.filter(dietary_tags__contains=[dietary])
    if min_price is not None:
        listings = listings.filter(price__gte=min_price)
    if max_price is not None:
        listings = listings.filter(price__lte=max_price)
    available_only = request.GET.get("available") == "1"
    if available_only:
        now = timezone.now()
        open_stock = ListingStock.objects.filter(
            listing_id=OuterRef("pk"),
            slot__seller_id=OuterRef("seller_id"),
            slot__is_active=True,
            slot__ends_at__gt=now,
            capacity__gt=F("held") + F("committed"),
        ).filter(
            Q(slot__order_type=FulfillmentSlot.OrderType.STANDARD)
            | Q(slot__preorder_deadline__gt=now)
        )
        listings = listings.alias(has_open_stock=Exists(open_stock)).filter(has_open_stock=True)

    paginator = Paginator(listings.order_by("dish__name", "seller__storefront_name", "pk"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "catalog/list.html", {
        "page_obj": page_obj,
        "countries": Country.objects.all(),
        "query": query,
        "selected_country": country,
        "selected_dietary": dietary if dietary in DIETARY_TAGS else "",
        "dietary_choices": DIETARY_TAGS.items(),
        "min_price": request.GET.get("min_price", ""),
        "max_price": request.GET.get("max_price", ""),
        "available_only": available_only,
    })


def listing_detail(request, pk):
    listing = get_object_or_404(
        FoodListing.objects.public().select_related("dish", "dish__country", "seller"), pk=pk,
    )
    now = timezone.now()
    stocks = ListingStock.objects.filter(
        listing=listing, slot__is_active=True, slot__ends_at__gt=now,
    ).select_related("slot").order_by("slot__starts_at")
    slots = []
    for stock in stocks:
        slot = stock.slot
        if stock.available < 1:
            continue
        if slot.order_type == FulfillmentSlot.OrderType.PREORDER and (
            slot.preorder_deadline is None or slot.preorder_deadline <= now
        ):
            continue
        slot.available = stock.available
        slots.append(slot)
    return render(request, "catalog/detail.html", {"listing": listing, "slots": slots})
