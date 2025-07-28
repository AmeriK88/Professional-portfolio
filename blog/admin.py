from django.utils.html import format_html
from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import FieldTextFilter, RangeDateTimeFilter
from unfold.decorators import action
from unfold.enums import ActionVariant

from .models import Post


@admin.register(Post)
class PostAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_sheet = True
    list_filter_submit = True

    list_display = ("title", "image_thumb", "created_at", "updated_at")
    list_display_links = ("title",)
    search_fields = ("title", "content")
    list_filter = [
        ("title", FieldTextFilter),
        ("created_at", RangeDateTimeFilter),
        ("updated_at", RangeDateTimeFilter),
    ]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25

    # Acciones bulk (opcionales)
    actions = ["clear_image"]

    @action(description="Clear image", icon="image_not_supported", variant=ActionVariant.WARNING)
    def clear_image(self, request, queryset):
        cleared = 0
        for post in queryset:
            if post.image:
                post.image.delete(save=False)  # borra el fichero físico
                post.image = None
                post.save(update_fields=["image"])
                cleared += 1
        self.message_user(request, f"Removed image from {cleared} post(s).")

    @admin.display(description="Image")
    def image_thumb(self, obj):
        if obj.image:
            return format_html("<img src='{}' width='120' alt='{}' />", obj.image.url, obj.title)
        return "-"
