from django.contrib.auth.models import AbstractUser
from django.db import models
from django.templatetags.static import static

# Avatares predefinidos (pon las imágenes en /static/avatars/presets/)
AVATAR_CHOICES = [
    ("dev", "Dev"),
    ("ninja", "Ninja"),
    ("robot", "Robot"),
    ("wizard", "Wizard"),
    ("astro", "Astronauta"),
]

def user_avatar_upload_to(instance, filename):
    # Si algún día quieres permitir subida desde admin:
    return f"avatars/{instance.pk}/{filename}"

class User(AbstractUser):
    """
    User con:
      - avatar (subida opcional; útil para admin o futuro)
      - avatar_choice (selección de preset estático)
    """
    avatar = models.ImageField(upload_to=user_avatar_upload_to, blank=True, null=True)
    avatar_choice = models.CharField(max_length=16, blank=True, default="", choices=AVATAR_CHOICES)

    @property
    def display_name(self) -> str:
        full = self.get_full_name().strip()
        return full or self.username

    @property
    def avatar_url(self) -> str:
        """
        1) avatar subido
        2) avatar_choice => /static/avatars/presets/<choice>.png
        3) default => /static/images/default-avatar.png
        """
        if self.avatar:
            try:
                return self.avatar.url
            except Exception:
                pass
        if self.avatar_choice:
            return static(f"avatars/presets/{self.avatar_choice}.png")
        return static("images/default-avatar.png")

    def __str__(self) -> str:
        return self.display_name
