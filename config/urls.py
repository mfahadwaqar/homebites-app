from django.contrib import admin
from django.urls import include, path

from core.views import HomeView


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("account/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
]



