from django import forms
from django.contrib.auth.forms import UserCreationForm

from accounts.models import User


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "display_name")



class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "email")
        labels = {"display_name": "Name", "email": "Email"}
