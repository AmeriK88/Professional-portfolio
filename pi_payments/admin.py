import json
import requests
from django.conf import settings
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateTimeFilter
from unfold.decorators import action
from unfold.enums import ActionVariant

from .models import Payment  # ✅ importa desde tu app, no desde orders


def _pi_headers():
    key = getattr(settings, "PI_API_KEY", None)
    return {"Authorization": f"Key {key}", "Content-Type": "application/json"}

def _fetch_pi_payment(pid: str):
    base = "https://api.minepi.com"
    r = requests.get(f"{base}/v2/payments/{pid}", headers=_pi_headers(), timeout=20)
    if not r.ok:
        return False, {"status_code": r.status_code, "text": r.text}
    return True, r.json()


# Conveniencia por si algún día cambias a TextChoices
S_INITIATED = getattr(Payment, "INITIATED", "initiated")
S_CONFIRMED = getattr(Payment, "CONFIRMED", "confirmed")
S_FAILED    = getattr(Payment, "FAILED",    "failed")


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

    # ---- acciones ----
    actions = ["sync_from_pi", "mark_failed", "mark_initiated", "mark_confirmed"]

    @action(description="Sync from Pi", icon="sync", variant=ActionVariant.INFO)
    def sync_from_pi(self, request, queryset):
        ok_n, fail_n = 0, 0
        for p in queryset:
            pid = getattr(p, "provider_payment_id", None)
            if not pid:
                fail_n += 1
                continue
            try:
                ok, info = _fetch_pi_payment(pid)
                if not ok:
                    fail_n += 1
                    continue
                # auditoría
                p.raw_payload = info

                status = (info.get("status") or "").lower()
                txid = (info.get("transaction") or {}).get("txid") or info.get("txid")
                if status == "completed" or txid:
                    p.status = S_CONFIRMED

                p.save(update_fields=["raw_payload", "status"])
                ok_n += 1
            except Exception:
                fail_n += 1
        self.message_user(request, f"Sync OK: {ok_n} | errors: {fail_n}")

    @action(description="Mark failed", icon="error", variant=ActionVariant.DANGER)
    def mark_failed(self, request, queryset):
        n = queryset.update(status=S_FAILED)
        self.message_user(request, f"Marked failed: {n}")

    @action(description="Mark initiated", icon="play_arrow", variant=ActionVariant.WARNING)
    def mark_initiated(self, request, queryset):
        n = queryset.update(status=S_INITIATED)
        self.message_user(request, f"Marked initiated: {n}")

    @action(description="Mark confirmed", icon="check_circle", variant=ActionVariant.SUCCESS)
    def mark_confirmed(self, request, queryset):
        n = queryset.update(status=S_CONFIRMED)
        self.message_user(request, f"Marked confirmed: {n}")

    # ---- helpers visuales ----

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
        val = (getattr(obj, "status", "") or "").lower()
        color_map = {
            S_INITIATED.lower(): "#0dcaf0",
            S_CONFIRMED.lower(): "#198754",
            S_FAILED.lower():    "#dc3545",
        }
        color = color_map.get(val, "#6c757d")
        label = getattr(obj, "get_status_display", lambda: obj.status)()
        return format_html(
            "<span style='padding:2px 8px;border-radius:12px;background:{};color:#fff'>{}</span>",
            color, label
        )

    @admin.display(description="Payload")
    def raw_payload_pretty(self, obj):
        data = getattr(obj, "raw_payload", None)
        if not data:
            return "-"
        try:
            raw = json.dumps(data, indent=2, ensure_ascii=False)
            if len(raw) > 8000:
                raw = raw[:8000] + "\n…(truncated)…"
            return format_html("<pre style='white-space:pre-wrap;max-height:320px;overflow:auto'>{}</pre>", raw)
        except Exception:
            return format_html("<pre>{}</pre>", data)
