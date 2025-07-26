import os, uuid
from django.db import models
from django.core.validators import FileExtensionValidator

def preview_upload_path(instance, filename):
    """
    Guarda siempre en projects/previews/ con un nombre UUID muy corto
    y conserva la extensión original (.mp4 o .gif).
    """
    ext = os.path.splitext(filename)[1]  # ej. ".mp4"
    # genera un UUID de 8 caracteres hexadecimales
    short_id = uuid.uuid4().hex[:8]
    return f"projects/previews/{short_id}{ext}"

class Project(models.Model):
    name        = models.CharField(max_length=200)
    description = models.TextField()
    image       = models.ImageField(upload_to='projects/')
    preview     = models.FileField(
        upload_to=preview_upload_path,
        max_length=255,  # 255 es más que suficiente si acortamos el nombre
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['mp4', 'gif'])],
        help_text='Sube un .mp4 o .gif para la previsualización.'
    )
    url         = models.URLField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
