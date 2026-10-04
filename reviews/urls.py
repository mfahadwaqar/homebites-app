from django.urls import path

from reviews import views


app_name = "reviews"

urlpatterns = [
    path("orders/<int:order_id>/new/", views.new_review, name="new"),
    path("sellers/<int:seller_id>/", views.seller_reviews, name="seller_reviews"),
    path("sellers/<int:seller_id>/report/", views.report_seller, name="report_seller"),
    path("listings/<int:listing_id>/report/", views.report_listing, name="report_listing"),
    path("reports/<int:report_id>/received/", views.report_received, name="report_received"),
    path("moderation/", views.moderation_queue, name="moderation_queue"),
    path("moderation/reviews/<int:pk>/", views.moderate_review_view, name="moderate_review"),
    path("moderation/reports/<int:pk>/", views.resolve_report_view, name="resolve_report"),
]
