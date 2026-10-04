from django.urls import include, path
from config.urls import urlpatterns as project_urlpatterns


urlpatterns = [*project_urlpatterns, path("payments/", include("payments.urls"))]
