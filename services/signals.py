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
    """
    Compresión muy ligera para previews: 3s, 240px ancho, 12fps, CRF 32,
    ~300 kbps máx, sin audio. Escribe a archivo temporal y hace replace atómico.
    Devuelve True si fue OK (no lanza excepciones).
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        log.error("ffmpeg no encontrado en PATH; se omite compresión para %s", src_abs)
        return False

    os.makedirs(os.path.dirname(dst_abs), exist_ok=True)
    tmp_abs = dst_abs + ".tmp"

    cmd = [
        ffmpeg, "-y",
        "-i", src_abs,
        "-t", "3",                        # 3 segundos
        "-r", "12",                       # 12 fps
        "-vf", "scale=240:trunc(ow/a/2)*2",  # ancho 240px; alto par manteniendo aspect
        "-c:v", "libx264",
        "-crf", "32",
        "-maxrate", "300k", "-bufsize", "600k",
        "-preset", "faster",
        "-movflags", "+faststart",
        "-an",                            # sin audio
        tmp_abs,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if res.stderr:
            log.info("ffmpeg: %s", res.stderr[:2000])
        if not (os.path.exists(tmp_abs) and os.path.getsize(tmp_abs) > 0):
            try:
                if os.path.exists(tmp_abs):
                    os.remove(tmp_abs)
            except OSError:
                pass
            return False
        os.replace(tmp_abs, dst_abs)
        return True
    except subprocess.CalledProcessError as e:
        log.exception("ffmpeg falló (%s): %s", e.returncode, (e.stderr or "")[:2000])
        try:
            if os.path.exists(tmp_abs):
                os.remove(tmp_abs)
        except OSError:
            pass
        return False
    except Exception:
        try:
            if os.path.exists(tmp_abs):
                os.remove(tmp_abs)
        except OSError:
            pass
        log.exception("Error inesperado comprimiendo %s", src_abs)
        return False

@receiver(post_save, sender=Service)
def compress_and_clean_service_preview(sender, instance, **kwargs):
    """
    1) Solo actúa sobre .mp4 que no terminen en '_s.mp4'.
    2) Genera service_previews/<base>_s.mp4 con compresión ligera.
    3) Asigna el campo preview a esa versión.
    4) Elimina el fichero original.
    5) Nunca lanza excepción (evita 500 en admin).
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
        src_abs = field.path  # requiere FileSystemStorage local
    except Exception:
        log.warning("Storage no expone .path; se omite compresión para %s", field.name)
        return

    base, _ = os.path.splitext(os.path.basename(src_abs))
    small_name = f"{base}_s.mp4"
    # Mantengo tu convención previa de carpeta:
    small_rel = os.path.join("service_previews", small_name).replace("\\", "/")
    small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)

    # Si ya existe el comprimido: reasigna y limpia
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

    # Asignar destino y borrar origen
    instance.preview.name = small_rel
    instance._compressing_preview = True
    instance.save(update_fields=["preview"])
    instance._compressing_preview = False
    try:
        if os.path.exists(src_abs):
            os.remove(src_abs)
    except OSError:
        pass
