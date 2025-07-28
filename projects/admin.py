from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import FieldTextFilter, RangeDateTimeFilter
from django.contrib import admin
from .models import Project
import os, subprocess
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from unfold.decorators import action
from unfold.enums import ActionVariant

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

    # ✅ Acciones BULK (reciben queryset)
    actions = ["recompress_selected_previews"]

    @action(description="Recompress selected previews")
    def recompress_selected_previews(self, request: HttpRequest, queryset: QuerySet):
        ok = 0
        failed = 0
        for p in queryset:
            if not (p.preview and p.preview.name.lower().endswith(".mp4")):
                continue
            src = p.preview.path
            base = os.path.splitext(os.path.basename(src))[0]
            small_rel = f"projects/previews/{base}_s.mp4"
            small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)

            try:
                completed = subprocess.run(
                    [
                        "ffmpeg","-y","-i",src,
                        "-vf","scale=320:-2,fps=10",
                        "-c:v","libx264","-crf","28",
                        "-preset","veryfast","-movflags","+faststart",
                        small_abs
                    ],
                    capture_output=True, text=True
                )
                if completed.returncode == 0 and os.path.exists(small_abs) and os.path.getsize(small_abs) > 0:
                    p.preview.name = small_rel
                    with transaction.atomic():
                        p.save(update_fields=["preview"])
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

    # ✅ Acciones POR FILA (reciben object_id) con icono
    actions_row = ["recompress_row"]

    @action(description="Recompress", icon="movie", variant=ActionVariant.INFO)
    def recompress_row(self, request: HttpRequest, object_id: int):
        p = Project.objects.filter(pk=object_id).first()
        if not p or not (p.preview and p.preview.name.lower().endswith(".mp4")):
            return redirect(reverse("admin:projects_project_changelist"))

        src = p.preview.path
        base = os.path.splitext(os.path.basename(src))[0]
        small_rel = f"projects/previews/{base}_s.mp4"
        small_abs = os.path.join(settings.MEDIA_ROOT, small_rel)

        completed = subprocess.run(
            [
                "ffmpeg","-y","-i",src,
                "-vf","scale=320:-2,fps=10",
                "-c:v","libx264","-crf","28",
                "-preset","veryfast","-movflags","+faststart",
                small_abs
            ],
            capture_output=True, text=True
        )
        if completed.returncode == 0 and os.path.exists(small_abs) and os.path.getsize(small_abs) > 0:
            p.preview.name = small_rel
            with transaction.atomic():
                p.save(update_fields=["preview"])
                try:
                    os.remove(src)
                except OSError:
                    pass

        return redirect(reverse("admin:projects_project_changelist"))

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
