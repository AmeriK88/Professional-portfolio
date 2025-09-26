from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import FieldTextFilter, RangeDateTimeFilter
from django.contrib import admin
from .models import Project
import os, subprocess, shutil, logging
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from unfold.decorators import action
from unfold.enums import ActionVariant

logger = logging.getLogger(__name__)

def _compress_mp4(src_abs: str, dst_abs: str) -> bool:
    """
    Compresión muy ligera: 3s, 240px ancho, 12fps, CRF 32, máx ~300kbps, sin audio.
    Escribe a archivo temporal y hace replace atómico. Devuelve True si OK.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.error("ffmpeg no encontrado en PATH; se omite compresión para %s", src_abs)
        return False

    os.makedirs(os.path.dirname(dst_abs), exist_ok=True)
    tmp_abs = dst_abs + ".tmp"

    cmd = [
        ffmpeg, "-y",
        "-i", src_abs,
        "-t", "3",
        "-r", "12",
        "-vf", "scale=240:trunc(ow/a/2)*2",
        "-c:v", "libx264",
        "-crf", "32",
        "-maxrate", "300k", "-bufsize", "600k",
        "-preset", "faster",
        "-movflags", "+faststart",
        "-an",
        tmp_abs,
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if res.stderr:
            logger.info("ffmpeg: %s", res.stderr[:2000])
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
        logger.exception("ffmpeg falló (%s): %s", e.returncode, (e.stderr or "")[:2000])
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
        logger.exception("Error inesperado comprimiendo %s", src_abs)
        return False

@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_sheet = True
    list_filter_submit = True

    list_display = ("name", "preview_thumb", "created_at")
    list_display_links = ("name",)
    search_fields = ("name", "description")
    list_filter = [
        ("name", FieldTextFilter),
        ("created_at", RangeDateTimeFilter),
    ]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    actions_on_top = True
    actions_on_bottom = False

    # ✅ Acción BULK
    actions = ["recompress_selected_previews"]

    @action(description="Recompress selected previews")
    def recompress_selected_previews(self, request: HttpRequest, queryset: QuerySet):
        ok = 0
        failed = 0
        skipped = 0
        for p in queryset:
            if not (p.preview and p.preview.name):
                skipped += 1
                continue

            name_lower = p.preview.name.lower()
            if not name_lower.endswith(".mp4") or name_lower.endswith("_s.mp4"):
                skipped += 1
                continue

            try:
                src = p.preview.path
            except Exception:
                skipped += 1
                continue

            base = os.path.splitext(os.path.basename(src))[0]
            small_rel = f"projects/previews/{base}_s.mp4"
            small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)

            if os.path.exists(small_abs):
                # Ya existe comprimido; sólo reasigna y limpia
                p.preview.name = small_rel.replace("\\", "/")
                with transaction.atomic():
                    p.save(update_fields=["preview"])
                    try:
                        if os.path.exists(src):
                            os.remove(src)
                    except OSError:
                        pass
                ok += 1
                continue

            if _compress_mp4(src, small_abs):
                p.preview.name = small_rel.replace("\\", "/")
                try:
                    with transaction.atomic():
                        p.save(update_fields=["preview"])
                        try:
                            if os.path.exists(src):
                                os.remove(src)
                        except OSError:
                            pass
                    ok += 1
                except Exception:
                    failed += 1
            else:
                failed += 1

        self.message_user(request, f"Recompressed {ok} • Failed {failed} • Skipped {skipped}")

    # ✅ Acción por fila
    actions_row = ["recompress_row"]

    @action(description="Recompress", icon="movie", variant=ActionVariant.INFO)
    def recompress_row(self, request: HttpRequest, object_id: int):
        p = Project.objects.filter(pk=object_id).first()
        if not p or not (p.preview and p.preview.name):
            return redirect(reverse("admin:projects_project_changelist"))

        name_lower = p.preview.name.lower()
        if (not name_lower.endswith(".mp4")) or name_lower.endswith("_s.mp4"):
            return redirect(reverse("admin:projects_project_changelist"))

        try:
            src = p.preview.path
        except Exception:
            return redirect(reverse("admin:projects_project_changelist"))

        base = os.path.splitext(os.path.basename(src))[0]
        small_rel = f"projects/previews/{base}_s.mp4"
        small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)

        if os.path.exists(small_abs) or _compress_mp4(src, small_abs):
            p.preview.name = small_rel.replace("\\", "/")
            try:
                with transaction.atomic():
                    p.save(update_fields=["preview"])
                    try:
                        if os.path.exists(src):
                            os.remove(src)
                    except OSError:
                        pass
            except Exception:
                pass

        return redirect(reverse("admin:projects_project_changelist"))

    @admin.display(description="Preview")
    def preview_thumb(self, obj: Project):
        """
        Evita cargar <video> en la lista (reduce red/tiempo).
        - Si hay MP4: muestra enlace "▶ Preview" + thumb de imagen si existe.
        - Si hay imagen: muestra la imagen.
        """
        if obj.preview:
            url = obj.preview.url
            if url.lower().endswith(".mp4"):
                if obj.image:
                    return format_html(
                        "<div style='display:flex;align-items:center;gap:.5rem;'>"
                        "<a href='{0}' target='_blank' rel='noopener'>▶ Preview</a>"
                        "<img src='{1}' width='120' style='border-radius:6px' />"
                        "</div>",
                        url, obj.image.url
                    )
                return format_html("<a href='{}' target='_blank' rel='noopener'>▶ Preview</a>", url)

            # Si el preview es imagen
            return format_html("<img src='{}' width='160' style='border-radius:6px'/>", url)

        if obj.image:
            return format_html("<img src='{}' width='160' style='border-radius:6px'/>", obj.image.url)

        return "-"
