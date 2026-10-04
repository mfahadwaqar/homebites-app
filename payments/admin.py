from django.contrib import admin

from payments.models import PaymentAttempt


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = ("mock_reference", "order", "method", "amount", "state", "created_at")
    list_filter = ("state", "method")
    search_fields = ("mock_reference", "order__id", "order__buyer__username")
    readonly_fields = ("order", "method", "amount", "idempotency_key", "mock_reference", "state", "created_at", "resolved_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
