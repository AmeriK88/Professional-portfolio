# services/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.urls import reverse
import os
import uuid

# ========= Validadores =========

def validate_file_size(value, max_mb=20):
    if value.size and value.size > max_mb * 1024 * 1024:
        raise ValidationError(f"El archivo supera {max_mb} MB.")

def validate_image_ext(value):
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise ValidationError("Solo imágenes JPG/PNG/WEBP.")

def validate_preview_ext(value):
    ext = os.path.splitext(value.name)[1].lower()
    # Recomendado: solo MP4 o imagen (evitar GIF por peso/egreso)
    if ext not in (".mp4", ".jpg", ".jpeg", ".png", ".webp"):
        raise ValidationError("Preview debe ser MP4 o imagen (JPG/PNG/WEBP).")

# ========= Helpers de ruta =========

def preview_upload_path(instance, filename):
    """service_previews/<uuid8>.<ext> (ext en minúscula)"""
    ext = os.path.splitext(filename)[1].lower()
    short_id = uuid.uuid4().hex[:8]
    return f"service_previews/{short_id}{ext}"

def image_upload_path(instance, filename):
    """service_images/<uuid8>.<ext> (ext en minúscula)"""
    ext = os.path.splitext(filename)[1].lower()
    short_id = uuid.uuid4().hex[:8]
    return f"service_images/{short_id}{ext}"

def _unique_slug(instance, base: str, max_length: int = 60) -> str:
    """
    Genera un slug único recortando y añadiendo sufijo -2, -3, ... si hace falta.
    Evita colisiones sin romper el límite de longitud.
    """
    Model = instance.__class__
    slug_base = slugify(base)[:max_length] or "item"
    candidate = slug_base
    i = 2
    while Model.objects.filter(slug=candidate).exclude(pk=instance.pk).exists():
        suffix = f"-{i}"
        candidate = (slug_base[: max_length - len(suffix)]) + suffix
        i += 1
    return candidate

# ========= Modelos =========

class Service(models.Model):
    title       = models.CharField(max_length=200)
    description = models.TextField()
    price       = models.DecimalField(max_digits=8, decimal_places=2)

    slug        = models.SlugField(max_length=60, unique=True, null=True, blank=True, editable=False)

    image       = models.ImageField(
        upload_to=image_upload_path,
        blank=True,
        null=True,
        validators=[validate_image_ext, lambda f: validate_file_size(f, 5)],  # 5 MB máx imagen
    )
    preview     = models.FileField(
        upload_to=preview_upload_path,
        max_length=255,
        blank=True,
        null=True,
        validators=[validate_preview_ext, lambda f: validate_file_size(f, 20)],  # 20 MB máx preview
        help_text="Sube un MP4 ligero (recomendado) o una imagen (WEBP/JPG/PNG).",
    )

    is_active   = models.BooleanField(default=True)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "title"]
        indexes = [
            models.Index(fields=["-is_active", "title"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["price"]),
            models.Index(fields=["-created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(self, self.title, max_length=self._meta.get_field("slug").max_length)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("services:detail", args=[self.slug])

    def __str__(self):
        return self.title

    # Helpers útiles en plantillas/admin
    @property
    def is_preview_video(self) -> bool:
        return bool(self.preview and self.preview.name.lower().endswith(".mp4"))

    @property
    def display_media_url(self) -> str:
        """URL preferida para mostrar: preview si existe, si no image."""
        if self.preview:
            return self.preview.url
        return self.image.url if self.image else ""

class ServiceFAQ(models.Model):
    service  = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=200)
    answer   = models.TextField()
    order    = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return f"{self.service.title} · {self.question[:40]}"

class ServiceFeature(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="features")
    text    = models.TextField()
    order   = models.PositiveIntegerField(default=0)
    icon    = models.CharField(
        max_length=50,
        blank=True,
        help_text="Opcional: nombre de icono (p.ej. 'check', 'bolt', etc.)."
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Feature"
        verbose_name_plural = "Features"

    def __str__(self):
        return f"{self.service.title} · {self.text[:40]}"
