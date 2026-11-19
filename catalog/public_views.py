from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator
from django.db.models import Avg, Count, Exists, F, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from catalog.models import Country, DIETARY_TAGS, DISH_CATEGORIES, FoodListing
from fulfillment.models import DemoLocation
from orders.models import FulfillmentSlot, ListingStock
from orders.availability import attach_availability, bookable_stocks


def _nonnegative_price(value):
    try:
        price = Decimal(value)
    except (InvalidOperation, TypeError):
        return None
    return price if price.is_finite() and price >= 0 else None


def attach_ratings(listings):
    """One aggregate query: approved review average and count per listing on this page."""
    from reviews.models import Review
    rows = (Review.objects.public().filter(order__items__listing__in=[l.pk for l in listings])
            .values("order__items__listing").annotate(avg=Avg("rating"), n=Count("pk", distinct=True)))
    stats = {row["order__items__listing"]: row for row in rows}
    for listing in listings:
        row = stats.get(listing.pk)
        listing.rating_avg = row["avg"] if row else None
        listing.rating_count = row["n"] if row else 0


def listing_list(request):
    listings = FoodListing.objects.public().select_related("dish", "dish__country", "seller__user")
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
    category = request.GET.get("category", "").strip().lower()
    if category in DISH_CATEGORIES:
        listings = listings.filter(dish__category=category)
    area = request.GET.get("area", "").strip()
    if area.isdigit():
        listings = listings.filter(seller__pickup_location_id=int(area))
    from reviews.models import Review
    rating_sq = (Review.objects.public().filter(order__items__listing=OuterRef("pk"))
                 .values("order__items__listing").annotate(a=Avg("rating")).values("a")[:1])
    listings = listings.annotate(rating_avg_db=Subquery(rating_sq))
    min_rating = request.GET.get("min_rating", "").strip()
    try:
        min_rating_value = Decimal(min_rating) if min_rating else None
    except InvalidOperation:
        min_rating_value = None
    if min_rating_value is not None and min_rating_value > 0:
        listings = listings.filter(rating_avg_db__gte=min_rating_value)
    available_only = request.GET.get("available") == "1"
    if available_only:
        now = timezone.now()
        open_stock = bookable_stocks(at=now).filter(listing_id=OuterRef("pk"))
        listings = listings.alias(has_open_stock=Exists(open_stock)).filter(has_open_stock=True)

    sort = request.GET.get("sort", "").strip()
    ordering = {
        "price_asc": ("price", "dish__name", "pk"),
        "price_desc": ("-price", "dish__name", "pk"),
        "rating": (F("rating_avg_db").desc(nulls_last=True), "dish__name", "pk"),
    }.get(sort, ("dish__name", "seller__storefront_name", "pk"))
    paginator = Paginator(listings.order_by(*ordering), 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    page_obj.object_list = attach_availability(page_obj.object_list)
    attach_ratings(page_obj.object_list)
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
        "category_choices": DISH_CATEGORIES.items(),
        "selected_category": category if category in DISH_CATEGORIES else "",
        "areas": DemoLocation.objects.filter(seller_pickups__isnull=False).distinct().order_by("label"),
        "selected_area": area if area.isdigit() else "",
        "selected_min_rating": min_rating if min_rating_value else "",
        "selected_sort": sort if sort in ("price_asc", "price_desc", "rating") else "",
        "kept_params": [(k, v) for k, v in request.GET.items() if k not in ("sort", "page")],
    })


def listing_detail(request, pk):
    listing = get_object_or_404(
        FoodListing.objects.public().select_related("dish", "dish__country", "seller__user"), pk=pk,
    )
    now = timezone.now()
    attach_availability([listing], at=now)
    slots = []
    for window in listing.availability.windows:
        slot = window.slot
        slot.available = window.remaining
        slot.booking_cutoff = window.cutoff
        slots.append(slot)
    review_item = None
    token = None
    if request.user.is_authenticated:
        from orders.models import CartItem
        from orders.services.cart import review_token
        try:
            review_id = int(request.GET.get("review_cart_item", ""))
            if not 0 < review_id <= 9223372036854775807:
                review_id = None
        except (ValueError, TypeError):
            review_id = None
        review_item = CartItem.objects.select_related("listing", "cart").filter(
            pk=review_id,
            cart__buyer=request.user, listing=listing,
        ).first()
        if review_item:
            token = review_token(review_item)
    from reviews.models import Review
    review_qs = Review.objects.public().filter(order__items__listing=listing).select_related("order__buyer").distinct()
    summary = review_qs.aggregate(count=Count("pk", distinct=True), average=Avg("rating"))
    reviews = list(review_qs.order_by("-created_at", "-pk")[:5])
    return render(request, "catalog/detail.html", {
        "listing": listing, "slots": slots, "review_item": review_item, "review_token": token,
        "reviews": reviews, "review_summary": summary,
    })
