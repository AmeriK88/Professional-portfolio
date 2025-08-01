# Generated by Django 5.1.3 on 2025-07-26 01:32

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='preview',
            field=models.FileField(blank=True, help_text='Carga un .mp4 o un .gif para la vista previa.', max_length=255, null=True, upload_to='service_previews/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['mp4', 'gif'])]),
        ),
    ]
