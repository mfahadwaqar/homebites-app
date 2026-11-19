from django.urls import path
from demo import views

app_name = "demo"
urlpatterns = [path("readiness/", views.readiness, name="readiness"), path("refresh/", views.refresh, name="refresh")]
