from __future__ import annotations
from pathlib import Path
import json, requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.http import FileResponse, Http404, JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.db import IntegrityError, transaction
import uuid

from .forms import (
    CustomUserCreationForm,
    ProfileUpdateForm,
    StyledAuthenticationForm,
)
from .models import AVATAR_CHOICES

PI_API_BASE = "https://api.minepi.com/v2"
User = get_user_model()


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


def _pick_backend() -> str:
    """
    Elige el backend de autenticación para login() cuando no venimos de authenticate().
    Prioriza ModelBackend si existe; si no, el primero configurado.
    """
    for b in settings.AUTHENTICATION_BACKENDS:
        if b.endswith("ModelBackend"):
            return b
    return settings.AUTHENTICATION_BACKENDS[0]


# ---------- Pi Auth ----------
@require_POST
@csrf_protect
def pi_login(request):
    # 1. Validar JSON recibido.
    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"ok": False, "reason": "JSON inválido"},
            status=400,
        )

    if not isinstance(data, dict):
        return JsonResponse(
            {"ok": False, "reason": "Formato inválido"},
            status=400,
        )

    token = data.get("accessToken")

    if not isinstance(token, str) or not token.strip():
        return JsonResponse(
            {"ok": False, "reason": "Falta accessToken"},
            status=400,
        )

    token = token.strip()

    # 2. Verificar token directamente con Pi Network.
    try:
        response = requests.get(
            f"{PI_API_BASE}/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )
    except requests.RequestException:
        return JsonResponse(
            {
                "ok": False,
                "reason": "No se pudo contactar con Pi Network",
            },
            status=502,
        )

    if not response.ok:
        return JsonResponse(
            {
                "ok": False,
                "reason": "Token de Pi inválido",
            },
            status=401,
        )

    try:
        me = response.json()
    except ValueError:
        return JsonResponse(
            {
                "ok": False,
                "reason": "Respuesta inválida de Pi Network",
            },
            status=502,
        )

    if not isinstance(me, dict):
        return JsonResponse(
            {
                "ok": False,
                "reason": "Datos de usuario inválidos",
            },
            status=502,
        )

    # 3. Validar identificador de Pi.
    pi_uid = me.get("uid")
    pi_username = me.get("username")

    if not isinstance(pi_uid, str) or not pi_uid.strip():
        return JsonResponse(
            {
                "ok": False,
                "reason": "Pi no devolvió un UID válido",
            },
            status=502,
        )

    pi_uid = pi_uid.strip()

    if not isinstance(pi_username, str):
        pi_username = "pi_user"

    pi_username = pi_username.strip() or "pi_user"


    # 4. Buscar usuario mediante su identidad verificada de Pi.
    if len(pi_uid) > 128:
        return JsonResponse(
            {
                "ok": False,
                "reason": "Identificador de Pi demasiado largo",
            },
            status=502,
        )

    user = User.objects.filter(pi_uid=pi_uid).first()
    created = False

    # Protección temporal durante la migración de cuentas Pi.
    if user is None and getattr(settings, "PI_ACCOUNT_MIGRATION_LOCK", False):
        return JsonResponse(
            {
                "ok": False,
                "reason": "Migración de cuentas Pi en curso",
            },
            status=409,
        )

    if user is None:
        # Identificador interno aleatorio: no depende del UID
        # ni puede reservarse prediciendo el nombre de usuario.
        username = f"pi_{uuid.uuid4().hex}"

        try:
            with transaction.atomic():
                user = User(
                    username=username,
                    pi_uid=pi_uid,
                    email="",
                )
                user.set_unusable_password()
                user.save(force_insert=True)
                created = True

        except IntegrityError:
            # Otra solicitud pudo crear la misma identidad
            # simultáneamente. Recuperamos únicamente por pi_uid.
            user = User.objects.filter(pi_uid=pi_uid).first()

            if user is None:
                return JsonResponse(
                    {
                        "ok": False,
                        "reason": "No se pudo crear la cuenta",
                    },
                    status=409,
                )

    if not user.is_active:
        return JsonResponse(
            {
                "ok": False,
                "reason": "Cuenta desactivada",
            },
            status=403,
        )


    # 5. Crear sesión autenticada.
    login(
        request,
        user,
        backend=_pick_backend(),
    )

    if created:
        messages.success(
            request,
            "Cuenta Pi creada. ¡Bienvenido!",
        )
    else:
        messages.success(
            request,
            "Has iniciado sesión. ¡Bienvenido de nuevo!",
        )

    return JsonResponse({"ok": True})



@ensure_csrf_cookie
def pi_only_notice(request):
    return render(request, "accounts/pi_only.html", status=403)


# ---------- Auth Views ----------
@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(DjangoLoginView):
    """
    Login clásico (form) o sólo-Pi según flag en settings.
    """
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    authentication_form = StyledAuthenticationForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["PI_ONLY_LOGIN"] = getattr(settings, "PI_ONLY_LOGIN", False)
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Has iniciado sesión. ¡Bienvenido de nuevo!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Credenciales inválidas. Revisa usuario o contraseña.")
        return super().form_invalid(form)


# ---------- Registro / Perfil / Otros ----------
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
            login(request, user, backend=_pick_backend())  # explícito por consistencia
            messages.success(request, "Registro completado. ¡Bienvenido!")
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
        from orders.models import Order  # noqa: WPS433
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
        "avatar_choices": AVATAR_CHOICES,
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
            "redirect_to": "/",
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
