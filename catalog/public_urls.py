from django.urls import path

from catalog import public_views


app_name = "catalog"

urlpatterns = [
    path("", public_views.listing_list, name="list"),
    path("<int:pk>/", public_views.listing_detail, name="detail"),
]
