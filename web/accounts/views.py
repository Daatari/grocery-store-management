import hashlib
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .forms import RegistrationForm


class SignIn(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        # Basic per-process demo throttle; use shared edge throttling for a public deployment.
        key = "login:" + hashlib.sha256(request.META.get("REMOTE_ADDR", "").encode()).hexdigest()
        cache.add(key, 0, timeout=300)
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=300)
            count = 1
        if count > 20:
            return render(request, "error.html", {"message": "Too many sign-in attempts. Try again in five minutes."}, status=429)
        return super().post(request, *args, **kwargs)


@require_http_methods(["GET", "POST"])
def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()  # Only username/password; never accepts manager/staff flags.
        login(request, user)
        return redirect("stores")
    return render(request, "accounts/register.html", {"form": form})
