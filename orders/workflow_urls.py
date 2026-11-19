from django.urls import path

from orders import workflow_views


app_name = "orders_workflow"


urlpatterns = [
    path("", workflow_views.queue, name="queue"),
    path("<int:order_id>/", workflow_views.detail, name="detail"),
    path("<int:order_id>/accept/", workflow_views.accept, name="accept"),
    path("<int:order_id>/reject/", workflow_views.reject, name="reject"),
    path("<int:order_id>/advance/", workflow_views.advance, name="advance"),
    path("<int:order_id>/handoff/", workflow_views.handoff, name="handoff"),
]
