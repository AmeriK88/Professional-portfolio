from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify
from django.urls import reverse
import os
import uuid

def preview_upload_path(instance, filename):
    """
    Genera un nombre de 8 caracteres + extensión y lo guarda en
    service_previews/, garantizando rutas cortas.
    """
    ext = os.path.splitext(filename)[1]
    short_id = uuid.uuid4().hex[:8]
    return f"service_previews/{short_id}{ext}"

class Service(models.Model):
    title       = models.CharField(max_length=200)
    description = models.TextField()
    price       = models.DecimalField(max_digits=8, decimal_places=2)
    slug  = models.SlugField(max_length=60, unique=True, null=True, blank=True, editable=False) 
    image       = models.ImageField(
        upload_to='service_images/',
        blank=True,
        null=True
    )
    preview     = models.FileField(
        upload_to=preview_upload_path,
        max_length=255,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['mp4','gif'])],
        help_text='Carga un .mp4 o un .gif para la vista previa.'
    )
    is_active   = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:50]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("services:detail", args=[self.slug])

    def __str__(self):
        return self.title
    
    
class ServiceFAQ(models.Model):
    service  = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="faqs"
    )
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
    """
    Características/beneficios específicos por servicio.
    """
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="features"
    )
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
