from django.contrib import admin

from reviews.models import ModerationEvent, Report, Review


class AuditOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Review)
class ReviewAdmin(AuditOnlyAdmin):
    list_display = ("id", "order", "rating", "status", "created_at")
    list_filter = ("status", "rating")
    search_fields = ("order__id", "order__seller__storefront_name", "comment")


@admin.register(Report)
class ReportAdmin(AuditOnlyAdmin):
    list_display = ("id", "target", "reporter", "status", "created_at", "resolved_by")
    list_filter = ("status",)
    search_fields = ("reason", "seller__storefront_name", "listing__dish__name")

    @admin.display(description="Target")
    def target(self, obj):
        return obj.listing or obj.seller


@admin.register(ModerationEvent)
class ModerationEventAdmin(AuditOnlyAdmin):
    list_display = ("id", "action", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("reason", "actor__username")
