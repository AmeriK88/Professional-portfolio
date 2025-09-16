from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User
from .forms import CustomUserCreationForm
from django.utils.html import format_html


@admin.register(User)
class CustomUserAdmin(DjangoUserAdmin):
    """
    User admin afinado, sin romper el flujo estándar de Django.
    """
    # Usamos tu form de creación para incluir email en el alta
    add_form = CustomUserCreationForm

    # Listado
    list_display = (
        "username", "email", "full_name",
        "is_active", "is_staff",
        "last_login", "date_joined",
        "orders_count",   # <- se muestra "-" si no existe 'orders'
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    list_per_page = 25

    # Campos de sólo lectura
    readonly_fields = ("last_login", "date_joined")

    # Filtros horizontales para permisos
    filter_horizontal = ("groups", "user_permissions")

    # Fieldsets (vista de cambio)
    fieldsets = (
        (_("Cuenta"), {"fields": ("username", "password")}),
        (_("Información personal"), {"fields": ("first_name", "last_name", "email", "avatar")}),
        (_("Permisos"), {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("Fechas importantes"), {"fields": ("last_login", "date_joined")}),
    )

    # Fieldsets (vista de creación)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2", "is_active", "is_staff", "is_superuser", "groups"),
        }),
    )

    # Acciones
    actions = ["activate_users", "deactivate_users", "send_password_reset"]

    list_display = ("username", "email", "full_name", "is_active", "is_staff", "last_login", "date_joined", "orders_count", "avatar_thumb")

    @admin.display(description="Avatar")
    def avatar_thumb(self, obj):
        if obj.avatar:
            return format_html("<img src='{}' width='28' height='28' style='border-radius:50%'>", obj.avatar.url)
        return "—"


    @admin.display(description="Nombre completo", ordering="first_name")
    def full_name(self, obj):
        name = obj.get_full_name().strip()
        return name or "—"

    @admin.display(description="Pedidos")
    def orders_count(self, obj):
        """
        Devuelve nº de pedidos si existe la app 'orders'. Si no, muestra '-'.
        No rompe nada si no la tienes aún.
        """
        try:
            from orders.models import Order  # noqa: WPS433
        except Exception:
            return "—"
        try:
            return Order.objects.filter(user=obj).count()
        except Exception:
            return "—"

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activados {updated} usuario(s).", level=messages.SUCCESS)
    activate_users.short_description = "Activar seleccionados"

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Desactivados {updated} usuario(s).", level=messages.WARNING)
    deactivate_users.short_description = "Desactivar seleccionados"

    def send_password_reset(self, request, queryset):
        """
        Envía enlace de restablecimiento de contraseña a los emails de los seleccionados.
        Requiere EMAIL_BACKEND configurado. En desarrollo puedes usar:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
        """
        from django.contrib.auth.forms import PasswordResetForm
        sent = 0
        for email in queryset.values_list("email", flat=True):
            if not email:
                continue
            form = PasswordResetForm({"email": email})
            if form.is_valid():
                form.save(
                    request=request,
                    use_https=request.is_secure(),
                    # Usa tus plantillas si quieres personalizar:
                    # email_template_name="accounts/password_reset_email.html",
                    # subject_template_name="accounts/password_reset_subject.txt",
                )
                sent += 1
        if sent:
            self.message_user(request, f"Enviado enlace a {sent} usuario(s).", level=messages.INFO)
        else:
            self.message_user(request, "No había emails válidos en la selección.", level=messages.WARNING)
    send_password_reset.short_description = "Enviar enlace de restablecimiento"
