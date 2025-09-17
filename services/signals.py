import os
import shutil
import subprocess
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Service

log = logging.getLogger(__name__)

def _compress_mp4(src_abs: str, dst_abs: str) -> bool:
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
        "-an",
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

@receiver(post_save, sender=Service)
def compress_and_clean_service_preview(sender, instance, **kwargs):
    """
    1) Solo actúa sobre .mp4 que no terminen en '_s.mp4'.
    2) Genera una versión *base_s.mp4 en service_previews/.
    3) Asigna el campo preview a esa versión.
    4) Borra el fichero original. No lanza excepción.
    """
    if getattr(instance, "_compressing_preview", False):
        return

    field = getattr(instance, "preview", None)
    if not field or not getattr(field, "name", None):
        return

    name = field.name.lower()
    if not name.endswith(".mp4") or name.endswith("_s.mp4"):
        return

    try:
        src_abs = field.path
    except Exception:
        log.warning("Storage no expone .path; se omite compresión para %s", field.name)
        return

    base, _ = os.path.splitext(os.path.basename(src_abs))
    small_name = f"{base}_s.mp4"
    small_rel = os.path.join("service_previews", small_name).replace("\\", "/")
    small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)

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

    ok = _compress_mp4(src_abs, small_abs)
    if not ok:
        return

    instance.preview.name = small_rel
    instance._compressing_preview = True
    instance.save(update_fields=["preview"])
    instance._compressing_preview = False
    try:
        if os.path.exists(src_abs):
            os.remove(src_abs)
    except OSError:
        pass
