import os
import shutil
import subprocess
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Project

log = logging.getLogger(__name__)

def _compress_mp4(src_abs: str, dst_abs: str) -> bool:
    """Devuelve True si la compresión fue OK; no lanza excepción."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        log.error("ffmpeg no encontrado en PATH; se omite compresión para %s", src_abs)
        return False

    os.makedirs(os.path.dirname(dst_abs), exist_ok=True)

    cmd = [
        ffmpeg, "-y",
        "-i", src_abs,
        "-vf", "scale=320:trunc(ow/a/2)*2,fps=10",
        "-c:v", "libx264",
        "-crf", "28",
        "-preset", "veryfast",
        "-movflags", "+faststart",
        "-an",  # quita audio en previews (opcional)
        dst_abs,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if res.stderr:
            log.info("ffmpeg: %s", res.stderr[:2000])
        return os.path.exists(dst_abs) and os.path.getsize(dst_abs) > 0
    except subprocess.CalledProcessError as e:
        log.exception("ffmpeg falló (%s): %s", e.returncode, (e.stderr or "")[:2000])
        return False

@receiver(post_save, sender=Project)
def compress_preview(sender, instance, created, **kwargs):
    """
    Comprime un preview MP4 a *_s.mp4 solo una vez y elimina el original.
    Nunca lanza excepción (evita 500 en admin).
    """
    # Evita re-entradas si guardamos el propio objeto
    if getattr(instance, "_compressing_preview", False):
        return

    field = getattr(instance, "preview", None)
    if not field or not getattr(field, "name", None):
        return

    name_lower = field.name.lower()
    if not name_lower.endswith(".mp4"):
        return
    if name_lower.endswith("_s.mp4"):
        return

    # Paths
    try:
        src_abs = field.path  # requiere FileSystemStorage local
    except Exception:
        log.warning("Storage no expone .path; se omite compresión para %s", field.name)
        return

    base, _ = os.path.splitext(os.path.basename(src_abs))
    small_name = f"{base}_s.mp4"
    small_rel = os.path.join("projects", "previews", small_name).replace("\\", "/")
    small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)

    # Si ya existe el comprimido: asigna y borra origen
    if os.path.exists(small_abs):
        instance.preview.name = small_rel
        instance._compressing_preview = True
        instance.save(update_fields=["preview"])
        instance._compressing_preview = False
        try:
            if os.path.exists(src_abs):
                os.remove(src_abs)
        except OSError:
            pass
        return

    # Comprimir
    ok = _compress_mp4(src_abs, small_abs)
    if not ok:
        return

    # Asignar nuevo archivo y borrar original
    instance.preview.name = small_rel
    instance._compressing_preview = True
    instance.save(update_fields=["preview"])
    instance._compressing_preview = False
    try:
        if os.path.exists(src_abs):
            os.remove(src_abs)
    except OSError:
        pass
