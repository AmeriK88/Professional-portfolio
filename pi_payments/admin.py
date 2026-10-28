
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

from .models import Payment


# ============================================================
# PI NETWORK API
# ============================================================

def _pi_headers():
    key = getattr(settings, "PI_API_KEY", None)
    return {
        "Authorization": f"Key {key}",
        "Content-Type": "application/json",
    }


def _fetch_pi_payment(pid: str):
    base = "https://api.minepi.com"

    r = requests.get(
        f"{base}/v2/payments/{pid}",
        headers=_pi_headers(),
        timeout=20,
    )

    if not r.ok:
        return False, {
            "status_code": r.status_code,
            "text": r.text,
        }

    return True, r.json()


# ============================================================
# PAYMENT STATUS
# ============================================================

S_INITIATED = getattr(Payment, "INITIATED", "initiated")
S_CONFIRMED = getattr(Payment, "CONFIRMED", "confirmed")
S_FAILED = getattr(Payment, "FAILED", "failed")


# ============================================================
# PAYMENT ADMIN
# ============================================================

@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_sheet = True
    list_filter_submit = True

    # --------------------------------------------------------
    # LIST VIEW
    # --------------------------------------------------------

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

    search_fields = (
        "provider_payment_id",
        "order__number",
        "order__user__username",
        "order__user__email",
    )

    list_filter = (
        "status",
        "provider",
        "currency",
        ("created_at", RangeDateTimeFilter),
        ("completed_at", RangeDateTimeFilter),
    )

    ordering = ("-created_at",)
    list_per_page = 25

    # --------------------------------------------------------
    # DETAIL VIEW — READ ONLY
    # --------------------------------------------------------

    readonly_fields = (
        "order",
        "provider",
        "provider_payment_id",
        "status",
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

    # --------------------------------------------------------
    # ADMIN ACTIONS
    # --------------------------------------------------------

    # Solo permitimos consultar el estado en Pi Network.
    # Nunca confirmar, iniciar o fallar pagos manualmente.
    actions = ["sync_from_pi"]

    @action(
        description="Sync from Pi",
        icon="sync",
        variant=ActionVariant.INFO,
    )
    def sync_from_pi(self, request, queryset):
        ok_n, fail_n = 0, 0

        for payment in queryset:
            pid = getattr(payment, "provider_payment_id", None)

            if not pid:
                fail_n += 1
                continue

            try:
                ok, info = _fetch_pi_payment(pid)

                if not ok:
                    fail_n += 1
                    continue

                # Conservar los datos originales del pago.
                raw = dict(payment.raw_payload or {})

                # Guardar la última respuesta de Pi Network
                # sin sobrescribir pricing ni otros datos.
                raw["pi_admin_sync"] = info

                # Actualización exclusivamente informativa.
                # QuerySet.update evita disparar señales post_save.
                Payment.objects.filter(pk=payment.pk).update(
                    raw_payload=raw
                )

                ok_n += 1

            except Exception:
                fail_n += 1

        self.message_user(
            request,
            f"Sync OK: {ok_n} | errors: {fail_n}",
        )

    # --------------------------------------------------------
    # DISPLAY HELPERS
    # --------------------------------------------------------

    @admin.display(description="Order")
    def order_link(self, obj):
        url = reverse(
            "admin:orders_order_change",
            args=[obj.order_id],
        )

        return format_html(
            "<a href='{}'>{}</a>",
            url,
            obj.order.number,
        )

    @admin.display(description="User")
    def user_email(self, obj):
        user = obj.order.user
        return f"{user.get_username()} · {user.email or '-'}"

    @admin.display(description="PID")
    def short_pid(self, obj):
        pid = obj.provider_payment_id or "-"

        if len(pid) <= 14:
            return pid

        return f"{pid[:6]}…{pid[-6:]}"

    @admin.display(description="Status")
    def status_badge(self, obj):
        val = (getattr(obj, "status", "") or "").lower()

        color_map = {
            S_INITIATED.lower(): "#0dcaf0",
            S_CONFIRMED.lower(): "#198754",
            S_FAILED.lower(): "#dc3545",
        }

        color = color_map.get(val, "#6c757d")

        label = getattr(
            obj,
            "get_status_display",
            lambda: obj.status,
        )()

        return format_html(
            "<span style='padding:2px 8px;"
            "border-radius:12px;"
            "background:{};"
            "color:#fff'>{}</span>",
            color,
            label,
        )

    @admin.display(description="Payload")
    def raw_payload_pretty(self, obj):
        data = getattr(obj, "raw_payload", None)

        if not data:
            return "-"

        try:
            raw = json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )

            if len(raw) > 8000:
                raw = raw[:8000] + "\n…(truncated)…"

            return format_html(
                "<pre style='white-space:pre-wrap;"
                "max-height:320px;"
                "overflow:auto'>{}</pre>",
                raw,
            )

        except Exception:
            return format_html(
                "<pre>{}</pre>",
                data,
            )
