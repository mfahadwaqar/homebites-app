from django.contrib import admin

from catalog.models import Country, Dish, FoodListing


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "country"]
    list_filter = ["country"]
    search_fields = ["code", "name"]
    readonly_fields = ["code", "country", "name"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FoodListing)
class FoodListingAdmin(admin.ModelAdmin):
    list_display = ["dish", "seller", "price", "status", "ingredients_reviewed", "calories_kcal", "nutrition_reviewed"]
    list_filter = ["status", "ingredients_reviewed", "dish__country"]
    search_fields = ["dish__name", "seller__storefront_name"]
