from django.urls import path

from payments import views


app_name = "payments"

urlpatterns = [
    path("<int:order_id>/", views.payment_page, name="pay"),
    path("<int:order_id>/result/", views.payment_result, name="result"),
]
