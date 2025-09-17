from django.contrib import admin
from django.utils.html import format_html, linebreaks
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import FieldTextFilter, RangeNumericFilter
from unfold.decorators import action
from unfold.enums import ActionVariant

import os
import subprocess
import shutil
import logging

from .models import Service, ServiceFAQ, ServiceFeature

logger = logging.getLogger(__name__)


# ---------- util: compresión coherente con signals (3s, 240px, 12fps, CRF32) ----------
def _compress_mp4(src_abs: str, dst_abs: str) -> bool:
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


# ---------- inlines ----------
class ServiceFeatureInline(admin.TabularInline):
    model = ServiceFeature
    extra = 3
    fields = ("order", "text", "icon")
    ordering = ("order", "id")
    classes = ("collapse",)


class ServiceFAQInline(admin.TabularInline):
    model = ServiceFAQ
    extra = 1
    fields = ("order", "question", "answer")
    ordering = ("order", "id")
    classes = ("collapse",)


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_sheet = True
    list_filter_submit = True

    inlines = [ServiceFeatureInline, ServiceFAQInline]

    list_display = ("title", "price", "is_active", "preview_thumb")
    list_editable = ("price", "is_active")
    list_display_links = ("title",)
    search_fields = ("title", "description")
    list_filter = [
        ("title", FieldTextFilter),
        ("price", RangeNumericFilter),
        "is_active",
    ]
    ordering = ("-is_active", "title")
    list_per_page = 25
    actions_on_top = True
    actions_on_bottom = False

    readonly_fields = ("pretty_description",)
    fields = (
        "title",
        "price",
        "is_active",
        "image",
        "preview",
        "description",
        "pretty_description",
    )

    # ---------- acciones bulk ----------
    actions = ["activate_selected", "deactivate_selected", "recompress_selected_previews"]

    @action(description="Activate selected")
    def activate_selected(self, request: HttpRequest, queryset: QuerySet):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} service(s).")

    @action(description="Deactivate selected")
    def deactivate_selected(self, request: HttpRequest, queryset: QuerySet):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} service(s).")

    @action(description="Recompress selected previews")
    def recompress_selected_previews(self, request: HttpRequest, queryset: QuerySet):
        ok = failed = skipped = 0
        for s in queryset:
            if not (s.preview and s.preview.name):
                skipped += 1
                continue

            name_lower = s.preview.name.lower()
            if (not name_lower.endswith(".mp4")) or name_lower.endswith("_s.mp4"):
                skipped += 1
                continue

            try:
                src = s.preview.path
            except Exception:
                skipped += 1
                continue

            base = os.path.splitext(os.path.basename(src))[0]
            small_rel = f"service_previews/{base}_s.mp4"
            small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)

            if os.path.exists(small_abs):
                s.preview.name = small_rel.replace("\\", "/")
                with transaction.atomic():
                    s.save(update_fields=["preview"])
                    try:
                        if os.path.exists(src):
                            os.remove(src)
                    except OSError:
                        pass
                ok += 1
                continue

            if _compress_mp4(src, small_abs):
                s.preview.name = small_rel.replace("\\", "/")
                try:
                    with transaction.atomic():
                        s.save(update_fields=["preview"])
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

    # ---------- acciones por fila ----------
    actions_row = ["activate_row", "deactivate_row", "recompress_row"]

    @action(description="Activate", icon="check_circle", variant=ActionVariant.SUCCESS)
    def activate_row(self, request: HttpRequest, object_id: int):
        Service.objects.filter(pk=object_id).update(is_active=True)
        return redirect(reverse("admin:services_service_changelist"))

    @action(description="Deactivate", icon="cancel", variant=ActionVariant.DANGER)
    def deactivate_row(self, request: HttpRequest, object_id: int):
        Service.objects.filter(pk=object_id).update(is_active=False)
        return redirect(reverse("admin:services_service_changelist"))

    @action(description="Recompress", icon="movie", variant=ActionVariant.INFO)
    def recompress_row(self, request: HttpRequest, object_id: int):
        s = Service.objects.filter(pk=object_id).first()
        if not s or not (s.preview and s.preview.name):
            return redirect(reverse("admin:services_service_changelist"))

        name_lower = s.preview.name.lower()
        if (not name_lower.endswith(".mp4")) or name_lower.endswith("_s.mp4"):
            return redirect(reverse("admin:services_service_changelist"))

        try:
            src = s.preview.path
        except Exception:
            return redirect(reverse("admin:services_service_changelist"))

        base = os.path.splitext(os.path.basename(src))[0]
        small_rel = f"service_previews/{base}_s.mp4"
        small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)

        if os.path.exists(small_abs) or _compress_mp4(src, small_abs):
            s.preview.name = small_rel.replace("\\", "/")
            try:
                with transaction.atomic():
                    s.save(update_fields=["preview"])
                    try:
                        if os.path.exists(src):
                            os.remove(src)
                    except OSError:
                        pass
            except Exception:
                pass

        return redirect(reverse("admin:services_service_changelist"))

    # ---------- columnas ----------
    @admin.display(description="Preview")
    def preview_thumb(self, obj: Service):
        """
        Evita <video> en la lista (reduce red/tiempo):
        - Si hay MP4: link "▶ Preview" + miniatura de image si existe.
        - Si el preview es imagen, renderiza la imagen.
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
            return format_html("<img src='{}' width='160' style='border-radius:6px'/>", url)

        if obj.image:
            return format_html("<img src='{}' width='160' style='border-radius:6px'/>", obj.image.url)

        return "-"

    @admin.display(description="Description (preview)")
    def pretty_description(self, obj: Service):
        if not obj or not obj.description:
            return "-"
        html = linebreaks(obj.description)
        return format_html("<div style='line-height:1.4'>{}</div>", html)
