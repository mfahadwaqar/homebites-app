from django import forms

from orders.models import FulfillmentSlot, ListingStock


class SellerSlotForm(forms.ModelForm):
    starts_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )
    ends_at = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )
    preorder_deadline = forms.DateTimeField(
        required=False, input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = FulfillmentSlot
        fields = [
            "order_type", "starts_at", "ends_at", "preorder_deadline",
            "allows_pickup", "allows_delivery", "is_active",
        ]


class StockCapacityForm(forms.ModelForm):
    class Meta:
        model = ListingStock
        fields = ["capacity"]
