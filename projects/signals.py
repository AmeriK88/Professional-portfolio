# projects/signals.py

import os
import subprocess
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Project

@receiver(post_save, sender=Project)
def compress_preview(sender, instance, created, **kwargs):
    """
    Comprime un preview MP4 a *_s.mp4 solo una vez: si el nombre
    ya termina en '_s.mp4' no hace nada. Además elimina el archivo
    original tras guardar la versión comprimida.
    """
    if not instance.preview:
        return

    name_lower = instance.preview.name.lower()
    # 1) Sólo .mp4
    if not name_lower.endswith('.mp4'):
        return

    # 2) Si ya es la versión pequeña, salimos
    if name_lower.endswith('_s.mp4'):
        return

    # 3) Rutas y nombres
    src = instance.preview.path
    base, _ = os.path.splitext(os.path.basename(src))
    small_name = f"{base}_s.mp4"
    small_rel  = f"projects/previews/{small_name}"
    small_abs  = os.path.join(settings.MEDIA_ROOT, small_rel)

    # 4) Si ya existe la versión comprimida, actualizar nombre y borrar viejos
    if os.path.exists(small_abs):
        instance.preview.name = small_rel
        instance.save(update_fields=['preview'])
        try:
            os.remove(src)
        except OSError:
            pass
        return

    # 5) Llamada a ffmpeg para comprimir
    subprocess.run([
        'ffmpeg', '-y',
        '-i', src,
        '-vf', 'scale=320:-2,fps=10',
        '-c:v', 'libx264',
        '-crf', '28',
        '-preset', 'veryfast',
        '-movflags', '+faststart',
        small_abs
    ], check=True)

    # 6) Guarda la ruta comprimida en el modelo
    instance.preview.name = small_rel
    instance.save(update_fields=['preview'])

    # 7) Elimina el archivo original ya que ya está comprimido
    try:
        os.remove(src)
    except OSError:
        pass
