import os
import subprocess
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Service

@receiver(post_save, sender=Service)
def compress_and_clean_service_preview(sender, instance, **kwargs):
    """
    1) Solo actúa sobre .mp4 que no terminen en '_s.mp4'.
    2) Genera una versión *base_s.mp4.
    3) Asigna el campo preview a esa versión.
    4) Borra el fichero .mp4 original para no duplicar espacio.
    """
    if not instance.preview:
        return

    name = instance.preview.name.lower()
    # 1) Debe ser MP4 y no ya comprimido
    if not name.endswith('.mp4') or name.endswith('_s.mp4'):
        return

    # 2) Rutas
    src_abs = instance.preview.path
    base, _ = os.path.splitext(os.path.basename(src_abs))
    small_name = f"{base}_s.mp4"
    small_rel  = f"service_previews/{small_name}"
    small_abs  = os.path.join(settings.MEDIA_ROOT, small_rel)

    # 3) Si ya existe, actualiza campo y elimina origen
    if os.path.exists(small_abs):
        instance.preview.name = small_rel
        instance.save(update_fields=['preview'])
        try:
            os.remove(src_abs)
        except OSError:
            pass
        return

    # 4) Llamada a ffmpeg
    subprocess.run([
        'ffmpeg', '-y',
        '-i', src_abs,
        '-vf', 'scale=320:-2,fps=10',
        '-c:v', 'libx264',
        '-crf', '28',
        '-preset', 'veryfast',
        '-movflags', '+faststart',
        small_abs
    ], check=True)

    # 5) Guarda la ruta comprimida y elimina el original
    instance.preview.name = small_rel
    instance.save(update_fields=['preview'])
    try:
        os.remove(src_abs)
    except OSError:
        pass
