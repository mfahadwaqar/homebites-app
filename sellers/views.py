from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import FoodListing
from orders.models import Order, OrderItem
from reviews.models import Review
from sellers.forms import FoodListingForm, SellerApplicationForm
from sellers.models import SellerProfile


@login_required
def apply(request):
    if SellerProfile.objects.filter(user=request.user).exists():
        return redirect("sellers:dashboard")
    form = SellerApplicationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        seller = form.save(commit=False)
        seller.user = request.user
        seller.save()
        return redirect("sellers:dashboard")
    return render(request, "sellers/apply.html", {"form": form})


@login_required
def dashboard(request):
    seller = SellerProfile.objects.filter(user=request.user).first()
    if seller is None:
        return redirect("sellers:apply")
    listings = FoodListing.objects.filter(seller=seller).select_related("dish", "dish__country")
    completed = Order.objects.filter(seller=seller, status=Order.Status.COMPLETED)
    totals = completed.aggregate(
        food_subtotal=Sum("food_subtotal"),
        commission_total=Sum("commission"),
        seller_earnings=Sum("seller_food_earnings"),
    )
    portions_sold = OrderItem.objects.filter(order__in=completed).aggregate(total=Sum("quantity"))["total"] or 0
    reviews = Review.objects.public().filter(order__seller=seller).aggregate(average=Avg("rating"))
    return render(request, "sellers/dashboard.html", {
        "seller": seller,
        "listings": listings,
        "completed_orders": completed.count(),
        "portions_sold": portions_sold,
        "food_subtotal": totals["food_subtotal"] or Decimal("0.00"),
        "commission_total": totals["commission_total"] or Decimal("0.00"),
        "seller_earnings": totals["seller_earnings"] or Decimal("0.00"),
        "rating_average": reviews["average"],
    })


@login_required
def profile_edit(request):
    seller = SellerProfile.objects.filter(user=request.user).first()
    if seller is None:
        return redirect("sellers:apply")
    form = SellerApplicationForm(request.POST or None, instance=seller)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("sellers:dashboard")
    return render(request, "sellers/profile_edit.html", {"form": form})


def storefront(request, pk):
    seller = get_object_or_404(SellerProfile, pk=pk, status=SellerProfile.Status.APPROVED, user__is_active=True)
    listings = FoodListing.objects.public().filter(seller=seller).select_related("dish", "dish__country")
    return render(request, "sellers/storefront.html", {"seller": seller, "listings": listings})


def _seller_for_edit(request):
    seller = SellerProfile.objects.filter(user=request.user).first()
    if seller is None:
        return None
    return seller


@login_required
def listing_create(request):
    seller = _seller_for_edit(request)
    if seller is None:
        return redirect("sellers:apply")
    form = FoodListingForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        listing = form.save(commit=False)
        listing.seller = seller
        if listing.status == FoodListing.Status.PUBLISHED and not seller.can_sell:
            form.add_error("status", "Only approved active sellers can publish.")
        elif FoodListing.objects.filter(seller=seller, dish=listing.dish).exists():
            form.add_error("dish", "You already offer this dish.")
        else:
            form.save()
            return redirect("sellers:dashboard")
    return render(request, "sellers/listing_form.html", {"form": form, "seller": seller, "heading": "Create offer"})


@login_required
def listing_edit(request, pk):
    seller = _seller_for_edit(request)
    if seller is None:
        raise Http404
    listing = get_object_or_404(FoodListing, pk=pk, seller=seller)
    form = FoodListingForm(request.POST or None, request.FILES or None, instance=listing)
    if request.method == "POST" and form.is_valid():
        candidate = form.save(commit=False)
        if candidate.status == FoodListing.Status.PUBLISHED and not seller.can_sell:
            form.add_error("status", "Only approved active sellers can publish.")
        elif FoodListing.objects.filter(seller=seller, dish=candidate.dish).exclude(pk=listing.pk).exists():
            form.add_error("dish", "You already offer this dish.")
        else:
            form.save()
            return redirect("sellers:dashboard")
    return render(request, "sellers/listing_form.html", {"form": form, "seller": seller, "heading": "Edit offer"})
