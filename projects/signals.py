import os
import shutil
import subprocess
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Project

log = logging.getLogger(__name__)

# Binario configurable
FFMPEG = getattr(settings, "FFMPEG_CMD", "ffmpeg")


def _compress_mp4(src_abs: str, dst_abs: str) -> bool:
    """
    Comprime a un clip muy ligero (3s, 240px ancho, 12fps, CRF 32, ~300kbps, sin audio).
    Escribe a un archivo temporal y luego hace replace atómico.
    Devuelve True si fue OK; False en cualquier problema.
    """
    ffmpeg = shutil.which(FFMPEG)
    if not ffmpeg:
        log.warning("FFmpeg no encontrado en PATH (%s); omito %s", FFMPEG, src_abs)
        return False

    # Preflight
    if not (os.path.exists(src_abs) and os.path.getsize(src_abs) > 0):
        log.warning("Input inexistente o vacío: %s", src_abs)
        return False

    # Normaliza rutas
    src_abs = os.path.normpath(src_abs)
    dst_abs = os.path.normpath(dst_abs)

    os.makedirs(os.path.dirname(dst_abs), exist_ok=True)
    # Importante: termina en .mp4 (no .mp4.tmp) para que FFmpeg detecte el muxer
    tmp_abs = dst_abs[:-4] + ".tmp.mp4" if dst_abs.lower().endswith(".mp4") else dst_abs + ".tmp.mp4"

    cmd = [
        ffmpeg,
        "-nostdin",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", src_abs,
        "-t", "3",
        "-r", "12",
        "-vf", "scale=240:-2",   # robusto; mantiene aspect y altura par
        "-pix_fmt", "yuv420p",   # compatibilidad amplia
        "-c:v", "libx264",
        "-crf", "32",
        "-maxrate", "300k", "-bufsize", "600k",
        "-preset", "faster",
        "-movflags", "+faststart",
        "-an",
        "-f", "mp4",             # fuerza formato de salida
        tmp_abs,
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        if res.stderr:
            log.info("ffmpeg: %s", res.stderr[:2000])

        # valida salida temporal
        if not (os.path.exists(tmp_abs) and os.path.getsize(tmp_abs) > 0):
            try:
                if os.path.exists(tmp_abs):
                    os.remove(tmp_abs)
            except OSError:
                pass
            return False

        os.replace(tmp_abs, dst_abs)
        return True

    except subprocess.TimeoutExpired:
        log.error("FFmpeg timeout para %s", src_abs)
        try:
            if os.path.exists(tmp_abs):
                os.remove(tmp_abs)
        except OSError:
            pass
        return False

    except subprocess.CalledProcessError as e:
        log.exception("FFmpeg falló (%s). stderr: %s", e.returncode, (e.stderr or "")[:2000])
        try:
            if os.path.exists(tmp_abs):
                os.remove(tmp_abs)
        except OSError:
            pass
        return False

    except Exception:
        log.exception("Error inesperado comprimiendo %s", src_abs)
        try:
            if os.path.exists(tmp_abs):
                os.remove(tmp_abs)
        except OSError:
            pass
        return False


@receiver(post_save, sender=Project)
def compress_preview(sender, instance, created, **kwargs):
    """
    Comprime un preview MP4 a *_s.mp4 una vez y elimina el original.
    Nunca lanza excepción (evita 500 en admin).
    """
    if getattr(instance, "_compressing_preview", False):
        return

    field = getattr(instance, "preview", None)
    if not field or not getattr(field, "name", None):
        return

    name_lower = field.name.lower()
    if not name_lower.endswith(".mp4") or name_lower.endswith("_s.mp4"):
        return

    try:
        src_abs = field.path  # requiere FileSystemStorage local
    except Exception:
        log.info("Storage sin .path; omito compresión para %s", field.name)
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
