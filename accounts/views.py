import hashlib

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.http import HttpResponse
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
    max_failed_attempts = 5
    throttle_seconds = 15 * 60

    def _throttle_key(self):
        username = self.request.POST.get("username", "").strip().casefold()
        remote_address = self.request.META.get("REMOTE_ADDR", "")
        digest = hashlib.sha256(f"{remote_address}:{username}".encode("utf-8")).hexdigest()
        return f"homebites-login-failures:{digest}"

    def post(self, request, *args, **kwargs):
        if cache.get(self._throttle_key(), 0) >= self.max_failed_attempts:
            response = HttpResponse("Too many sign-in attempts. Try again in 15 minutes.", status=429)
            response["Retry-After"] = str(self.throttle_seconds)
            return response
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        key = self._throttle_key()
        if cache.add(key, 1, timeout=self.throttle_seconds):
            return super().form_invalid(form)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=self.throttle_seconds)
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._throttle_key())
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

