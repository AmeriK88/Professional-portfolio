from django.contrib import admin
from django.utils.html import format_html, linebreaks
from django.conf import settings
from django.db import transaction
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import FieldTextFilter, RangeNumericFilter
from unfold.decorators import action
from unfold.enums import ActionVariant
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
import os, subprocess

from .models import Service


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_sheet = True
    list_filter_submit = True

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

    # Mostramos la descripción formateada como SOLO LECTURA
    readonly_fields = ("pretty_description",)

    # Incluimos description (editable) + pretty_description (preview)
    fields = (
        "title",
        "price",
        "is_active",
        "image",
        "preview",
        "description",         # editable (textarea)
        "pretty_description",  # preview solo lectura
    )

    # --- Acciones bulk ---
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
        ok = failed = 0
        for s in queryset:
            if not (s.preview and s.preview.name.lower().endswith(".mp4")):
                continue
            src = s.preview.path
            base = os.path.splitext(os.path.basename(src))[0]
            small_rel = f"service_previews/{base}_s.mp4"
            small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)
            try:
                completed = subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", src,
                        "-vf", "scale=320:-2,fps=10",
                        "-c:v", "libx264", "-crf", "28",
                        "-preset", "veryfast", "-movflags", "+faststart",
                        small_abs
                    ],
                    capture_output=True, text=True
                )
                if completed.returncode == 0 and os.path.exists(small_abs) and os.path.getsize(small_abs) > 0:
                    s.preview.name = small_rel
                    with transaction.atomic():
                        s.save(update_fields=["preview"])
                        try:
                            os.remove(src)
                        except OSError:
                            pass
                    ok += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
        self.message_user(request, f"Recompressed {ok} file(s). {failed} failed.")

    # --- Acciones por fila ---
    actions_row = ["activate_row", "deactivate_row"]

    @action(description="Activate", icon="check_circle", variant=ActionVariant.SUCCESS)
    def activate_row(self, request: HttpRequest, object_id: int):
        Service.objects.filter(pk=object_id).update(is_active=True)
        return redirect(reverse("admin:services_service_changelist"))

    @action(description="Deactivate", icon="cancel", variant=ActionVariant.DANGER)
    def deactivate_row(self, request: HttpRequest, object_id: int):
        Service.objects.filter(pk=object_id).update(is_active=False)
        return redirect(reverse("admin:services_service_changelist"))

    # Vista previa en listado
    @admin.display(description="Preview")
    def preview_thumb(self, obj):
        if obj.preview:
            url = obj.preview.url
            if url.lower().endswith(".mp4"):
                return format_html("<video src='{}' width='160' muted loop playsinline></video>", url)
            return format_html("<img src='{}' width='160' />", url)
        if obj.image:
            return format_html("<img src='{}' width='160' />", obj.image.url)
        return "-"

    # ---- Descripción bonita / segura ----
    @admin.display(description="Description (preview)")
    def pretty_description(self, obj):
        if not obj or not obj.description:
            return "-"
        # Convierte \n a <p>/<br> y devuelve SafeString.
        html = linebreaks(obj.description)   
        return format_html("<div style='line-height:1.4'>{}</div>", html)
