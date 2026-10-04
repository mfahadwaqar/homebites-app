from django.contrib import admin

from sellers.models import SellerProfile


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ["storefront_name", "user", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["storefront_name", "user__username"]
    actions = ["approve_sellers", "reject_sellers", "suspend_sellers"]

    @admin.action(description="Approve selected sellers")
    def approve_sellers(self, request, queryset):
        queryset.update(status=SellerProfile.Status.APPROVED)

    @admin.action(description="Reject selected sellers")
    def reject_sellers(self, request, queryset):
        queryset.update(status=SellerProfile.Status.REJECTED)

    @admin.action(description="Suspend selected sellers")
    def suspend_sellers(self, request, queryset):
        queryset.update(status=SellerProfile.Status.SUSPENDED)
