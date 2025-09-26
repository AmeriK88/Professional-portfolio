from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateTimeFilter

from .models import Order, OrderItem


# ---------- Inlines ----------

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("service", "unit_price", "quantity")


# ---------- Order Admin ----------

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_sheet = True
    list_filter_submit = True

    list_display = ("number", "user_link", "status_badge", "total", "currency", "created_at", "paid_at")
    list_display_links = ("number",)
    search_fields = ("number", "user__username", "user__email")
    list_filter = (
        "status",
        "currency",
        ("created_at", RangeDateTimeFilter),
        ("paid_at", RangeDateTimeFilter),
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 25
    inlines = [OrderItemInline]

    @admin.display(description="User")
    def user_link(self, obj):
        url = reverse("admin:users_user_change", args=[obj.user_id])
        return format_html("<a href='{}'>{}</a>", url, obj.user)

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "pending":          "#6c757d",
            "awaiting_payment": "#0dcaf0",
            "paid":             "#198754",
            "cancelled":        "#dc3545",
            "refunded":         "#ffc107",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            "<span style='padding:2px 8px;border-radius:12px;background:{};color:#fff'>{}</span>",
            color, obj.get_status_display()
        )
