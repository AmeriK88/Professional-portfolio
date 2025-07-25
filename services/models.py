from django.db import models
from django.core.validators import FileExtensionValidator


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
        upload_to='service_previews/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'gif'])],
        help_text='Carga un .mp4 o un .gif para la vista previa.'
    )
    is_active   = models.BooleanField(default=True)

    def __str__(self):
        return self.title
