import os
import uuid
from django.db import models
from django.core.exceptions import ValidationError

# === Validadores =============================================================

def validate_file_size(value, max_mb):
    if value.size and value.size > max_mb * 1024 * 1024:
        raise ValidationError(f"El archivo supera {max_mb} MB.")

def validate_image_size_5mb(value):
    validate_file_size(value, 5)

def validate_preview_size_20mb(value):
    validate_file_size(value, 20)

def validate_image_ext(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise ValidationError("Solo imágenes JPG/PNG/WEBP.")

def validate_preview_ext(value):
    ext = os.path.splitext(value.name)[1].lower()
    # Recomendado: solo MP4 o imagen (sin GIF, para ahorrar)
    if ext not in (".mp4", ".jpg", ".jpeg", ".png", ".webp"):
        raise ValidationError("Preview debe ser MP4 o imagen (JPG/PNG/WEBP).")

# === Helpers de ruta =========================================================

def preview_upload_path(instance, filename):
    """projects/previews/<uuid8>.<ext>"""
    ext = os.path.splitext(filename)[1].lower()
    short_id = uuid.uuid4().hex[:8]
    return f"projects/previews/{short_id}{ext}"

def image_upload_path(instance, filename):
    """projects/images/<uuid8>.<ext>"""
    ext = os.path.splitext(filename)[1].lower()
    short_id = uuid.uuid4().hex[:8]
    return f"projects/images/{short_id}{ext}"

# === Modelo =================================================================

class Project(models.Model):
    name        = models.CharField(max_length=200)
    description = models.TextField()
    image       = models.ImageField(
        upload_to=image_upload_path,
        validators=[validate_image_ext, validate_image_size_5mb],  # 5 MB máx imagen
    )
    preview     = models.FileField(
        upload_to=preview_upload_path,
        max_length=255,
        blank=True,
        null=True,
        validators=[validate_preview_ext, validate_preview_size_20mb],  # 20 MB máx preview
        help_text="Sube un MP4 ligero (recomendado) o una imagen (WEBP/JPG/PNG).",
    )
    url         = models.URLField(blank=True, null=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.name

    # Helpers útiles en plantillas
    @property
    def is_preview_video(self) -> bool:
        return bool(self.preview and self.preview.name.lower().endswith(".mp4"))

    @property
    def display_media_url(self) -> str:
        """Devuelve la URL preferida para la card: preview si existe, si no image."""
        if self.preview:
            return self.preview.url
        return self.image.url if self.image else ""
