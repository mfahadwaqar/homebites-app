from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from django.templatetags.static import static as static_url
from django.views.generic import RedirectView

from accounts.views import HomeBitesLoginView
from core.views import HomeView


urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url=static_url("images/homebites-mark.svg"))),
    path("", HomeView.as_view(), name="home"),
    path("food/", include("catalog.public_urls")),
    path("demo/", include("demo.urls")),
    path("sellers/", include("sellers.urls")),
    path("reviews/", include("reviews.urls")),
    path("orders/", include("orders.urls")),
    path("seller-orders/", include("orders.workflow_urls")),
    path("payments/", include("payments.urls")),
    path("account/", include("accounts.urls")),
    path("accounts/login/", HomeBitesLoginView.as_view(), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



