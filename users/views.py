# users/views.py
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    CustomUserCreationForm,
    ProfileUpdateForm,
    StyledAuthenticationForm,
)
from .models import AVATAR_CHOICES


# ---------- Helpers ----------

def _safe_redirect(request, fallback: str | None = None):
    """
    Redirige a ?next= si es del mismo host; si no, usa 'fallback'.
    Si no hay fallback, cae en LOGIN_REDIRECT_URL (o '/').
    """
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    if fallback:
        return redirect(fallback)
    return redirect(getattr(settings, "LOGIN_REDIRECT_URL", "/"))


# ---------- Auth Views ----------

class LoginView(DjangoLoginView):
    """
    Login con mensajes de éxito/error y formulario estilizado.
    (Si en urls usas auth_views.LoginView, esta clase no se usa.)
    """
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    authentication_form = StyledAuthenticationForm

    def form_valid(self, form):
        messages.success(self.request, "Has iniciado sesión. ¡Bienvenido de nuevo!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Credenciales inválidas. Revisa usuario o contraseña.")
        return super().form_invalid(form)


def register(request):
    """
    Registro + login automático + mensaje + respeto de ?next=.
    """
    if request.user.is_authenticated:
        return redirect("users:profile")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registro completado. ¡Bienvenido!")
            # Fallback: perfil si no hay ?next=
            return _safe_redirect(request, fallback=reverse_lazy("users:profile"))
        messages.error(request, "Revisa los errores del formulario.")
    else:
        form = CustomUserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    """
    Perfil con:
      - Resumen de cuenta
      - Edición de first_name, last_name, email, avatar_choice (galería)
      - Atajos a cambiar contraseña / CV / logout
      - Enlace a pedidos si existe la app orders
    """
    # Como no hay subida de archivo, NO necesitamos request.FILES
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado correctamente.")
            return redirect("users:profile")
        messages.error(request, "Revisa los errores del formulario.")
    else:
        form = ProfileUpdateForm(instance=request.user)

    # ¿Existe orders?
    orders_url = None
    orders_count = None
    last_order = None
    try:
        from orders.models import Order  # si no existe, saltará ImportError
        try:
            orders_url = reverse("orders:list")
        except NoReverseMatch:
            orders_url = None
        try:
            orders_count = Order.objects.filter(user=request.user).count()
            last_order = Order.objects.filter(user=request.user).order_by("-id").first()
        except Exception:
            orders_count = None
            last_order = None
    except Exception:
        pass

    ctx = {
        "form": form,
        "orders_url": orders_url,
        "orders_count": orders_count,
        "last_order": last_order,
        "avatar_choices": AVATAR_CHOICES,  # para pintar la galería en la plantilla
    }
    return render(request, "accounts/profile.html", ctx)


def logout_view(request):
    """
    Cierra sesión y redirige. Acepta GET/POST.
    Respeta ?next= del mismo host; si no, LOGOUT_REDIRECT_URL o '/'.
    """
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return _safe_redirect(request, fallback=getattr(settings, "LOGOUT_REDIRECT_URL", "/"))


@login_required
def cv_gate(request):
    """Página intermedia: dispara la descarga y redirige al Home."""
    return render(
        request,
        "accounts/cv_gate.html",
        {
            "download_url": reverse_lazy("users:cv_download"),
            "redirect_to": "/",  # si tu home tiene name, usa reverse_lazy("NOMBRE_HOME")
        },
    )


@login_required
def cv_download(request):
    """
    Entrega el CV solo a usuarios autenticados.
    Lee desde /private/cv.pdf (fuera de static).
    """
    cv_path = Path(settings.BASE_DIR) / "private" / "cv.pdf"
    if not cv_path.exists():
        raise Http404("CV no disponible.")
    return FileResponse(
        open(cv_path, "rb"),
        as_attachment=True,
        filename="Jose_Felix_CV.pdf",
    )
