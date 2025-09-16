# users/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from .models import AVATAR_CHOICES

User = get_user_model()


class StyledAuthenticationForm(AuthenticationForm):
    """Login con estilos Bootstrap y autocompletado correcto."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.setdefault("class", "form-control")
        self.fields["username"].widget.attrs.setdefault("autocomplete", "username")
        self.fields["username"].widget.attrs.setdefault("placeholder", "Tu usuario")

        self.fields["password"].widget.attrs.setdefault("class", "form-control")
        self.fields["password"].widget.attrs.setdefault("autocomplete", "current-password")
        self.fields["password"].widget.attrs.setdefault("placeholder", "Tu contraseña")


class CustomUserCreationForm(UserCreationForm):
    """Registro con email obligatorio y estilos uniformes."""
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
