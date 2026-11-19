from django.urls import path

from sellers import slot_views, views

app_name = "sellers"

urlpatterns = [
    path("apply/", views.apply, name="apply"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("slots/", slot_views.slots, name="slots"),
    path("slots/new/", slot_views.slot_create, name="slot_create"),
    path("slots/<int:slot_id>/edit/", slot_views.slot_edit, name="slot_edit"),
    path("slots/<int:slot_id>/stock/<int:listing_id>/", slot_views.stock_set, name="stock_set"),
    path("offers/new/", views.listing_create, name="listing_create"),
    path("offers/<int:pk>/edit/", views.listing_edit, name="listing_edit"),
    path("offers/<int:pk>/delete/", views.listing_delete, name="listing_delete"),
    path("<int:pk>/", views.storefront, name="storefront"),
]
