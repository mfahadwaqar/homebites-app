from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class HomeBitesUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("HomeBites", {"fields": ("display_name",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("HomeBites", {"fields": ("email", "display_name")}),
    )

