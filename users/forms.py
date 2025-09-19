from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)

from .models import AVATAR_CHOICES
from .utils.recaptcha import verify_recaptcha 

User = get_user_model()


# ---------- Mixin reutilizable para reCAPTCHA v3 ----------
class RecaptchaV3Mixin(forms.Form):
    """
    Añade un campo hidden 'recaptcha_token' y valida reCAPTCHA v3 en clean().
    Sobrescribe 'recaptcha_action' en cada form que lo use.
    """
    recaptcha_token = forms.CharField(widget=forms.HiddenInput, required=False)
    recaptcha_action = "generic"

    def clean(self):
        cleaned = super().clean()
        token = self.data.get("recaptcha_token", "")
        ok, payload = verify_recaptcha(token, expected_action=self.recaptcha_action)
        if not ok:
            raise forms.ValidationError("Verificación reCAPTCHA fallida. Inténtalo de nuevo.")
        return cleaned


# ---------- Login ----------
class StyledAuthenticationForm(RecaptchaV3Mixin, AuthenticationForm):
    """Login con estilos Bootstrap, autocompletado y reCAPTCHA v3."""
    recaptcha_action = "login"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.setdefault("class", "form-control")
        self.fields["username"].widget.attrs.setdefault("autocomplete", "username")
        self.fields["username"].widget.attrs.setdefault("placeholder", "Tu usuario")

        self.fields["password"].widget.attrs.setdefault("class", "form-control")
        self.fields["password"].widget.attrs.setdefault("autocomplete", "current-password")
        self.fields["password"].widget.attrs.setdefault("placeholder", "Tu contraseña")


# ---------- Registro ----------
class CustomUserCreationForm(RecaptchaV3Mixin, UserCreationForm):
    """Registro con email obligatorio, estilos uniformes y reCAPTCHA v3."""
    recaptcha_action = "register"

    email = forms.EmailField(
        required=True,
        help_text="Necesario para notificaciones.",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "autocomplete": "email",
            "placeholder": "tu@correo.com",
        })
    )

    class Meta:  # Meta “plana” para que Pylance no se queje
        model = User
        fields = ("username", "email")
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "autocomplete": "username",
                "placeholder": "Tu usuario",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Uniforma estilos
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()
        # Placeholders para contraseñas
        self.fields["password1"].widget.attrs.update({
            "autocomplete": "new-password",
            "placeholder": "Mín. 8 caracteres",
        })
        self.fields["password2"].widget.attrs.update({
            "autocomplete": "new-password",
            "placeholder": "Repite la contraseña",
        })

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este email ya está en uso.")
        return email


# ---------- Perfil ----------
class ProfileUpdateForm(forms.ModelForm):
    """Edición de perfil con elección de avatar predefinido (sin subida)."""
    avatar_choice = forms.ChoiceField(
        choices=AVATAR_CHOICES,
        required=False,
        widget=forms.RadioSelect(attrs={"class": "avatar-radio"})
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "avatar_choice")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre"}),
            "last_name":  forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellidos"}),
            "email":      forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email", "placeholder": "tu@correo.com"}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("El email es obligatorio.")
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este email ya está en uso.")
        return email


# ---------- Cambio de contraseña ----------
class StyledPasswordChangeForm(PasswordChangeForm):
    """Cambio de contraseña con estilos Bootstrap."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].widget.attrs.update({
            "class": "form-control",
            "autocomplete": "current-password",
            "placeholder": "Tu contraseña actual",
        })
        self.fields["new_password1"].widget.attrs.update({
            "class": "form-control",
            "autocomplete": "new-password",
            "placeholder": "Nueva contraseña",
        })
        self.fields["new_password2"].widget.attrs.update({
            "class": "form-control",
            "autocomplete": "new-password",
            "placeholder": "Repite la nueva contraseña",
        })
