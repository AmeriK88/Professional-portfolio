# pi_payments/views.py
import os, json, requests
from decimal import Decimal
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

# 👇 añade estos imports para actualizar tu BD
from orders.models import Order, Payment

PI_API_BASE = "https://api.minepi.com"
PI_API_KEY  = os.environ.get("PI_API_KEY")

def _auth_headers():
    return {"Authorization": f"Key {PI_API_KEY}", "Content-Type": "application/json"}

def _log(event, payload):  # cámbialo por logging si quieres
    print(f"[PI] {event} {now().isoformat()} :: {payload}")

def _fetch_pi_payment(pid: str):
    """Lee el pago desde la API de Pi para obtener metadata (order_number, nonce, etc.)."""
    r = requests.get(f"{PI_API_BASE}/v2/payments/{pid}", headers=_auth_headers(), timeout=20)
    try:
        data = r.json() if r.ok else {}
    except Exception:
        data = {}
    return r, data

def _attach_local_payment_from_info(pid: str, info: dict) -> Payment | None:
    """
    Conecta el pago de Pi (por pid) con nuestro Payment (por order_number en metadata).
    Guarda pid/raw y devuelve el objeto Payment o None si no se encontró.
    """
    meta = (info or {}).get("metadata") or {}
    order_number = meta.get("order_number")
    if not order_number:
        _log("link.missing_order_number", {"pid": pid, "meta": meta})
        return None

    try:
        pay = Payment.objects.select_related("order").get(order__number=order_number)
    except Payment.DoesNotExist:
        _log("link.local_payment_not_found", {"pid": pid, "order_number": order_number})
        return None

    # Guarda pid si no estaba y snapshot bruto
    changed = False
    if not pay.provider_payment_id:
        pay.provider_payment_id = pid
        changed = True

    raw = pay.raw_payload or {}
    raw.setdefault("pi_last_info", info)  # snapshot último conocido
    pay.raw_payload = raw

    if changed:
        pay.save(update_fields=["provider_payment_id", "raw_payload"])
    else:
        pay.save(update_fields=["raw_payload"])

    return pay

@require_POST
def pi_approve(request):
    data = json.loads(request.body.decode())
    pid  = data.get("paymentId")
    if not pid:
        return HttpResponseBadRequest("paymentId required")

    # 1) Lee info del pago para vincular a nuestro Payment
    r_info, info = _fetch_pi_payment(pid)
    if not r_info.ok:
        _log("approve.fetch_fail", {"pid": pid, "status": r_info.status_code, "body": r_info.text})

    pay = _attach_local_payment_from_info(pid, info)
    if pay:
        # Marca como iniciado si no lo estaba
        if pay.status != Payment.INITIATED:
            pay.status = Payment.INITIATED
            pay.save(update_fields=["status"])
        _log("approve.local_linked", {"pid": pid, "order": pay.order.number})

    # 2) Aprueba en Pi
    r = requests.post(f"{PI_API_BASE}/v2/payments/{pid}/approve", headers=_auth_headers(), timeout=20)
    _log("approve.api", {"pid": pid, "status": r.status_code, "body": r.text})
    return JsonResponse({"ok": r.ok})

@require_POST
def pi_complete(request):
    data = json.loads(request.body.decode())
    pid  = data.get("paymentId")
    txid = data.get("txid")
    if not pid or not txid:
        return HttpResponseBadRequest("paymentId and txid required")

    # 1) Lee info del pago y vincula con nuestro Payment
    r_info, info = _fetch_pi_payment(pid)
    if not r_info.ok:
        _log("complete.fetch_fail", {"pid": pid, "status": r_info.status_code, "body": r_info.text})
        return JsonResponse({"ok": False, "error": "cannot fetch payment"}, status=400)

    pay = _attach_local_payment_from_info(pid, info)
    if not pay:
        # Si no encontramos el pago local, no seguimos (preferible a marcar sin orden)
        return JsonResponse({"ok": False, "error": "local payment not found"}, status=404)

    # (Opcional) Validación de importe en π contra snapshot guardado en el checkout
    try:
        amount_pi = Decimal(str(info.get("amount", "0")))
        snap = (pay.raw_payload or {}).get("pricing", {})
        snap_amount_pi = Decimal(str(snap.get("amount_pi") or "0"))
        if snap_amount_pi and amount_pi and snap_amount_pi != amount_pi:
            _log("complete.amount_mismatch", {"pid": pid, "snap": str(snap_amount_pi), "pi": str(amount_pi)})
            return JsonResponse({"ok": False, "error": "amount mismatch"}, status=400)
    except Exception:
        pass  # si no hubiera snapshot/decimal, no bloqueamos

    # 2) Completa en Pi
    r = requests.post(
        f"{PI_API_BASE}/v2/payments/{pid}/complete",
        headers=_auth_headers(),
        json={"txid": txid},
        timeout=20
    )
    _log("complete.api", {"pid": pid, "status": r.status_code, "body": r.text})
    if not r.ok:
        return JsonResponse({"ok": False}, status=400)

    # 3) Marca como pagado en tu BD
    raw = pay.raw_payload or {}
    raw["pi_info_at_complete"] = info
    raw["txid"] = txid
    pay.raw_payload = raw
    pay.status = Payment.CONFIRMED
    pay.completed_at = now()
    if not pay.provider_payment_id:
        pay.provider_payment_id = pid
    pay.save(update_fields=["raw_payload", "status", "completed_at", "provider_payment_id"])

    order = pay.order
    if order.status != Order.PAID:
        order.status = Order.PAID
        order.paid_at = now()
        order.save(update_fields=["status", "paid_at"])

    return JsonResponse({"ok": True})

@require_POST
def pi_cancel(request):
    data = json.loads(request.body.decode())
    _log("cancel", data.get("paymentId"))
    return JsonResponse({"ok": True})

@csrf_exempt
@require_POST
def pi_webhook(request):  # opcional
    _log("webhook", request.body.decode())
    return HttpResponse(status=204)
