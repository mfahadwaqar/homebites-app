from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from accounts.forms import SignUpForm


class AnonymousRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:profile")
        return super().dispatch(request, *args, **kwargs)


class SignUpView(AnonymousRequiredMixin, CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy("login")
    template_name = "accounts/signup.html"


class HomeBitesLoginView(LoginView):
    redirect_authenticated_user = True


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

