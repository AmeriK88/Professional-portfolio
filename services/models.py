import os
import uuid
from django.db import models
from django.core.validators import FileExtensionValidator

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

    def __str__(self):
        return self.title
