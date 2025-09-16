import json
import requests
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.conf import settings

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateTimeFilter
from unfold.decorators import action
from unfold.enums import ActionVariant

from .models import Order, OrderItem, Payment

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
            "pending":  "#6c757d",
            "awaiting_payment": "#0dcaf0",
            "paid":     "#198754",
            "cancelled":"#dc3545",
            "refunded": "#ffc107",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html("<span style='padding:2px 8px;border-radius:12px;background:{};color:#fff'>{}</span>",
                           color, obj.get_status_display())


# ---------- Helpers para PI ----------

def _pi_headers():
    key = getattr(settings, "PI_API_KEY", None)
    return {"Authorization": f"Key {key}", "Content-Type": "application/json"}


def _fetch_pi_payment(pid: str):
    base = "https://api.minepi.com"
    r = requests.get(f"{base}/v2/payments/{pid}", headers=_pi_headers(), timeout=20)
    if not r.ok:
        return False, {"status_code": r.status_code, "text": r.text}
    return True, r.json()


# ---------- Payment Admin ----------

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_sheet = True
    list_filter_submit = True

    list_display = (
        "order_link",
        "user_email",
        "short_pid",
        "status_badge",
        "amount",
        "currency",
        "created_at",
        "completed_at",
    )
    list_display_links = ("order_link",)
    search_fields = ("provider_payment_id", "order__number", "order__user__username", "order__user__email")
    list_filter = (
        "status",
        "provider",
        "currency",
        ("created_at", RangeDateTimeFilter),
        ("completed_at", RangeDateTimeFilter),
    )
    ordering = ("-created_at",)
    list_per_page = 25

    readonly_fields = (
        "order",
        "provider",
        "provider_payment_id",
        "amount",
        "currency",
        "nonce",
        "created_at",
        "completed_at",
        "raw_payload_pretty",
    )

    fields = (
        "order",
        "provider",
        "provider_payment_id",
        ("amount", "currency"),
        ("status", "nonce"),
        ("created_at", "completed_at"),
        "raw_payload_pretty",
    )

    # ---- Acciones ----
    actions = ["sync_from_pi", "mark_failed", "mark_initiated"]

    @action(description="Sync from Pi", icon="sync", variant=ActionVariant.INFO)
    def sync_from_pi(self, request, queryset):
        ok_n, fail_n = 0, 0
        for p in queryset:
            pid = p.provider_payment_id
            if not pid:
                fail_n += 1
                continue
            try:
                ok, info = _fetch_pi_payment(pid)
                if not ok:
                    fail_n += 1
                    continue
                # Guarda payload para auditoría
                p.raw_payload = info

                # Si el payload indica estado final, actualiza
                # (no imponemos reglas estrictas: solo si claramente viene "completed")
                status = (info.get("status") or "").lower()
                txid = (info.get("transaction") or {}).get("txid") or info.get("txid")
                if status == "completed" or txid:
                    p.status = Payment.CONFIRMED
                p.save(update_fields=["raw_payload", "status"])
                ok_n += 1
            except Exception:
                fail_n += 1
        self.message_user(request, f"Sync OK: {ok_n} | errores: {fail_n}")

    @action(description="Mark failed", icon="error", variant=ActionVariant.DANGER)
    def mark_failed(self, request, queryset):
        n = queryset.update(status=Payment.FAILED)
        self.message_user(request, f"Marcados como failed: {n}")

    @action(description="Mark initiated", icon="play_arrow", variant=ActionVariant.WARNING)
    def mark_initiated(self, request, queryset):
        n = queryset.update(status=Payment.INITIATED)
        self.message_user(request, f"Marcados como initiated: {n}")

    # ---- Helpers visuales ----

    @admin.display(description="Order")
    def order_link(self, obj):
        url = reverse("admin:orders_order_change", args=[obj.order_id])
        return format_html("<a href='{}'>{}</a>", url, obj.order.number)

    @admin.display(description="User")
    def user_email(self, obj):
        u = obj.order.user
        return f"{u.get_username()} · {u.email or '-'}"

    @admin.display(description="PID")
    def short_pid(self, obj):
        pid = obj.provider_payment_id or "-"
        return pid if len(pid) <= 14 else f"{pid[:6]}…{pid[-6:]}"

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            Payment.INITIATED: "#0dcaf0",
            Payment.CONFIRMED: "#198754",
            Payment.FAILED:    "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html("<span style='padding:2px 8px;border-radius:12px;background:{};color:#fff'>{}</span>",
                           color, obj.get_status_display())

    @admin.display(description="Payload")
    def raw_payload_pretty(self, obj):
        if not obj.raw_payload:
            return "-"
        try:
            raw = json.dumps(obj.raw_payload, indent=2, ensure_ascii=False)
            # evita respuestas gigantes
            if len(raw) > 8000:
                raw = raw[:8000] + "\n…(truncated)…"
            return format_html("<pre style='white-space:pre-wrap;max-height:320px;overflow:auto'>{}</pre>", raw)
        except Exception:
            return format_html("<pre>{}</pre>", obj.raw_payload)
