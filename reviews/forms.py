from django import forms

from reviews.models import Report, Review


class ReviewForm(forms.Form):
    rating = forms.TypedChoiceField(
        choices=[(value, f"{value} / 5") for value in range(1, 6)], coerce=int,
    )
    comment = forms.CharField(required=False, max_length=2000, widget=forms.Textarea(attrs={"rows": 5}))


class ReportForm(forms.Form):
    reason = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 5}))

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()
        if not reason:
            raise forms.ValidationError("Explain the concern.")
        return reason


class ReviewDecisionForm(forms.Form):
    decision = forms.ChoiceField(choices=[
        (Review.Status.APPROVED, "Approve"), (Review.Status.HIDDEN, "Hide"),
    ])
    reason = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 3}))


class ReportDecisionForm(forms.Form):
    decision = forms.ChoiceField(choices=[
        (Report.Status.RESOLVED, "Resolve"), (Report.Status.DISMISSED, "Dismiss"),
    ])
    reason = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={"rows": 3}))
