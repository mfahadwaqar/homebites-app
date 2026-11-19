from django.urls import path

from orders import views


app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:listing_id>/", views.cart_add, name="add"),
    path("cart/item/<int:item_id>/", views.cart_update, name="update"),
    path("cart/item/<int:item_id>/review/", views.cart_acknowledge, name="acknowledge"),
    path("cart/quote/", views.cart_quote, name="quote"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("", views.order_list, name="list"),
    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/receipt/", views.order_receipt, name="receipt"),
    path("<int:pk>/cancel/", views.order_cancel, name="cancel"),
]
