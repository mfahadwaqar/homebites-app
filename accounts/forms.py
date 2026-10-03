from django.contrib.auth.forms import UserCreationForm

from accounts.models import User


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "display_name")

