# projects/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

def validate_preview(file):
    valid_mimes = ['video/mp4', 'image/gif']
    if file.content_type not in valid_mimes:
        raise ValidationError('Sólo se admiten MP4 o GIF para la vista previa.')

class Project(models.Model):
    name        = models.CharField(max_length=200)
    description = models.TextField()
    image       = models.ImageField(upload_to='projects/')
    preview     = models.FileField(
        upload_to='projects/previews/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'gif'])],
        help_text='Sube un archivo .mp4 o .gif para la previsualización.'
    )
    url         = models.URLField(blank=True, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
