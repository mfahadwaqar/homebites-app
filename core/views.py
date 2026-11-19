from django.views.generic import TemplateView

from catalog.models import Country, FoodListing
from orders.availability import attach_availability


HOME_BANDS = [
    ("TH", "Thailand", "Bright and herbal. Curries, noodles and salads.", "catalog/food/real/TH01-pad-thai.jpg", ("TH01", "TH02", "TH03")),
    ("PK", "Pakistan", "Slow-cooked and smoky. Biryani, karahi and nihari.", "catalog/food/real/PK02-nihari.jpg", ("PK01", "PK02", "PK04")),
    ("BD", "Bangladesh", "River fish, mustard and clay pots.", "catalog/food/real/BD03-shorshe-ilish.jpg", ("BD01", "BD03", "BD05")),
    ("NP", "Nepal", "Himalayan comfort. Momo, thukpa and dal bhat.", "catalog/food/real/NP01-chicken-momo.jpg", ("NP01", "NP04", "NP02")),
    ("IN", "India", "Tandoor, tiffin and street food.", "catalog/food/real/IN01-butter-chicken.jpg", ("IN01", "IN02", "IN06")),
]


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        countries = Country.objects.in_bulk()
        context["countries"] = [countries[code] for code in ("TH", "PK", "BD", "NP", "IN") if code in countries]
        listings = list(
            FoodListing.objects.public()
            .select_related("dish", "dish__country", "seller__user")
            .order_by("dish__name", "pk")
        )
        attach_availability(listings)
        by_country = {listing.dish.country_id: listing for listing in reversed(listings)}
        context["kitchens"] = [by_country[code] for code in ("TH", "PK", "BD", "NP", "IN") if code in by_country]
        featured_codes = ("TH01", "PK04", "BD03", "NP01", "IN01")
        by_dish = {listing.dish_id: listing for listing in reversed(listings)}
        context["featured"] = [by_dish[code] for code in featured_codes if code in by_dish]
        bands = []
        for code, name, line, image, dishes in HOME_BANDS:
            picked = [by_dish[d] for d in dishes if d in by_dish]
            if picked:
                bands.append({"code": code, "name": name, "line": line, "image": image, "listings": picked})
        context["bands"] = bands
        return context

