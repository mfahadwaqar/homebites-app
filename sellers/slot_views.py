from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import FoodListing
from orders.models import FulfillmentSlot, ListingStock, Order
from sellers.models import SellerProfile
from sellers.slot_forms import SellerSlotForm, StockCapacityForm
from orders.availability import booking_cutoff, window_problem
from django.utils import timezone


def _approved_seller(request):
    seller = SellerProfile.objects.filter(user=request.user).first()
    if seller is None or not seller.can_sell:
        raise PermissionDenied("An approved seller account is required.")
    return seller


@login_required
def slots(request):
    seller = _approved_seller(request)
    slot_rows = list(FulfillmentSlot.objects.filter(seller=seller).prefetch_related("stocks__listing__dish"))
    for slot in slot_rows:
        slot.booking_cutoff = booking_cutoff(slot)
        slot.booking_problem = window_problem(slot, at=timezone.now())
    listings = FoodListing.objects.filter(seller=seller).select_related("dish")
    return render(request, "sellers/slots/list.html", {
        "seller": seller, "slots": slot_rows, "listings": listings,
    })


@login_required
def slot_create(request):
    seller = _approved_seller(request)
    form = SellerSlotForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        slot = form.save(commit=False)
        slot.seller = seller
        slot.save()
        return redirect("sellers:slots")
    return render(request, "sellers/slots/form.html", {"form": form, "heading": "Create fulfillment slot"})


@login_required
def slot_edit(request, slot_id):
    seller = _approved_seller(request)
    slot = get_object_or_404(FulfillmentSlot, pk=slot_id, seller=seller)
    form = SellerSlotForm(request.POST or None, instance=slot)
    if request.method == "POST" and form.is_valid():
        locked_fields = {"order_type", "starts_at", "ends_at", "preorder_deadline", "allows_pickup", "allows_delivery"}
        if Order.objects.filter(slot=slot).exists() and locked_fields.intersection(form.changed_data):
            form.add_error(None, "A slot with orders cannot change its fulfillment terms. Deactivate it instead.")
        else:
            form.save()
            return redirect("sellers:slots")
    return render(request, "sellers/slots/form.html", {"form": form, "heading": "Edit fulfillment slot"})


@login_required
@transaction.atomic
def stock_set(request, slot_id, listing_id):
    seller = _approved_seller(request)
    slot = get_object_or_404(FulfillmentSlot, pk=slot_id, seller=seller)
    listing = get_object_or_404(FoodListing, pk=listing_id, seller=seller)
    stock = ListingStock.objects.select_for_update().filter(slot=slot, listing=listing).first()
    form = StockCapacityForm(request.POST or None, instance=stock)
    if request.method == "POST" and form.is_valid():
        stock = form.save(commit=False)
        stock.slot = slot
        stock.listing = listing
        stock.save()
        return redirect("sellers:slots")
    return render(request, "sellers/slots/stock.html", {
        "form": form, "slot": slot, "listing": listing, "stock": stock,
    })
