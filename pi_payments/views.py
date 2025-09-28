import os, json, requests
from decimal import Decimal
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

from orders.models import Order
from pi_payments.models import Payment

PI_API_BASE = "https://api.minepi.com"
PI_API_KEY  = os.environ.get("PI_API_KEY")

def _auth_headers():
    return {"Authorization": f"Key {PI_API_KEY}", "Content-Type": "application/json"}

def _log(event, payload):  # cámbialo por logging si quieres
    print(f"[PI] {event} {now().isoformat()} :: {payload}")

def _json(body: bytes | str) -> dict:
    try:
        return json.loads(body.decode() if isinstance(body, (bytes, bytearray)) else body) or {}
    except Exception:
        return {}

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
    data = _json(request.body)
    pid  = data.get("paymentId")
    if not pid:
        return HttpResponseBadRequest("paymentId required")

    # 1) Lee info del pago para vincular a nuestro Payment
    r_info, info = _fetch_pi_payment(pid)
    if not r_info.ok:
        _log("approve.fetch_fail", {"pid": pid, "status": r_info.status_code, "body": r_info.text})

    pay = _attach_local_payment_from_info(pid, info)

    # 2) Aprueba en Pi
    r = requests.post(f"{PI_API_BASE}/v2/payments/{pid}/approve", headers=_auth_headers(), timeout=20)
    _log("approve.api", {"pid": pid, "status": r.status_code, "body": r.text})

    if not r.ok:
        # Si Pi rechaza la aprobación, marcamos el pago como fallido y cancelamos la orden
        if pay:
            pay.mark_failed("approve rejected by Pi")
        return JsonResponse({"ok": False}, status=400)

    if pay:
        # Marca como iniciado si no lo estaba
        if pay.status != Payment.INITIATED:
            pay.status = Payment.INITIATED
            pay.save(update_fields=["status"])
        _log("approve.local_linked", {"pid": pid, "order": pay.order.number})

    return JsonResponse({"ok": True})

@require_POST
def pi_complete(request):
    data = _json(request.body)
    pid  = data.get("paymentId")
    txid = data.get("txid")
    if not pid or not txid:
        return HttpResponseBadRequest("paymentId and txid required")

    # 1) Lee info del pago y vincula con nuestro Payment
    r_info, info = _fetch_pi_payment(pid)
    if not r_info.ok:
        _log("complete.fetch_fail", {"pid": pid, "status": r_info.status_code, "body": r_info.text})
        # Si ni siquiera podemos leer la info, intenta marcar fallido si existe el Payment
        pay = Payment.objects.filter(provider_payment_id=pid).first()
        if pay:
            pay.mark_failed("cannot fetch payment before complete")
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
            # Marca como fallido y corta
            pay.mark_failed("amount mismatch")
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
        # Si Pi rechaza el complete, fallido
        pay.mark_failed("complete rejected by Pi")
        return JsonResponse({"ok": False}, status=400)

    # 3) Marca como pagado en tu BD
    raw = pay.raw_payload or {}
    raw["pi_info_at_complete"] = info
    raw["txid"] = txid
    pay.raw_payload = raw
    # usa helper para sincronizar orden
    pay.mark_confirmed(save_order=True)

    # Asegura provider_payment_id por si faltaba
    if not pay.provider_payment_id:
        pay.provider_payment_id = pid
        pay.save(update_fields=["provider_payment_id"])

    return JsonResponse({"ok": True})

@require_POST
def pi_cancel(request):
    # Endpoint para cuando el usuario cancela o no hay saldo suficiente
    # body: { "paymentId": "<pid>", "reason": "user_cancelled | insufficient_balance | ..." }
    data = _json(request.body)
    pid    = data.get("paymentId")
    reason = (data.get("reason") or "user_cancelled")
    if not pid:
        return HttpResponseBadRequest("paymentId required")

    # Intenta leer info para vincular y guardar motivo
    r_info, info = _fetch_pi_payment(pid)
    pay = _attach_local_payment_from_info(pid, info) or Payment.objects.filter(provider_payment_id=pid).first()
    if not pay:
        return JsonResponse({"ok": False, "error": "local payment not found"}, status=404)

    pay.mark_failed(reason)
    _log("cancel.mark_failed", {"pid": pid, "reason": reason})
    return JsonResponse({"ok": True})

@csrf_exempt
@require_POST
def pi_webhook(request):  # opcional
    # Estructuras habituales esperadas:
    # { "event": "approved|completed|cancelled|failed|rejected", "paymentId": "...", "txid": "...", "reason": "..." }
    # o bien { "status": "completed", "paymentId": "...", ... }
    data = _json(request.body)
    pid = data.get("paymentId") or data.get("payment_id")
    event = (data.get("event") or data.get("status") or "").strip().lower()
    reason = (data.get("reason") or data.get("error") or "").strip()

    if not pid:
        _log("webhook.missing_pid", data)
        return HttpResponseBadRequest("paymentId required")

    # Intenta leer info fresca de Pi y vincular el Payment local
    r_info, info = _fetch_pi_payment(pid)
    pay = _attach_local_payment_from_info(pid, info) or Payment.objects.filter(provider_payment_id=pid).first()

    if not pay:
        # Como último recurso, intenta por order_number del webhook directo (si viene)
        order_number = (data.get("metadata") or {}).get("order_number")
        if order_number:
            pay = Payment.objects.select_related("order").filter(order__number=order_number).first()

    if not pay:
        _log("webhook.local_payment_not_found", {"pid": pid, "event": event or "(none)"})
        return JsonResponse({"ok": False, "error": "local payment not found"}, status=404)

    # Idempotencia: si ya está confirmado y vuelve a llegar "completed", no hacemos nada
    if event in {"completed", "confirmed"} and pay.status == Payment.CONFIRMED:
        _log("webhook.completed_ignored_idempotent", {"pid": pid})
        return HttpResponse(status=204)

    # Guarda snapshot del último payload del webhook
    raw = pay.raw_payload or {}
    raw.setdefault("webhooks", []).append({"at": now().isoformat(), "data": data})
    if info:
        raw["pi_last_info"] = info
    pay.raw_payload = raw
    pay.save(update_fields=["raw_payload"])

    # Enruta por tipo de evento/estado
    if event in {"cancelled", "failed", "rejected", "declined"}:
        # Motivo si existe; si no, usa el propio event
        pay.mark_failed(reason or event)
        _log("webhook.mark_failed", {"pid": pid, "reason": reason or event})
        return HttpResponse(status=204)

    if event in {"approved"}:
        # Considera approved como iniciado si aún no está
        if pay.status != Payment.INITIATED:
            pay.status = Payment.INITIATED
            pay.save(update_fields=["status"])
        _log("webhook.mark_initiated", {"pid": pid})
        return HttpResponse(status=204)

    if event in {"completed", "confirmed"}:
        # Usa txid del webhook o de la info
        txid = data.get("txid") or (info.get("transaction") or {}).get("txid") or info.get("txid")
        if not txid:
            # Si no hay txid pero el estado dice completed, aún confirmamos para no quedarnos colgados
            pay.mark_confirmed(save_order=True)
        else:
            # Marca confirmado y deja txid en raw
            raw = pay.raw_payload or {}
            raw["txid"] = txid
            pay.raw_payload = raw
            pay.save(update_fields=["raw_payload"])
            pay.mark_confirmed(save_order=True)

        if not pay.provider_payment_id:
            pay.provider_payment_id = pid
            pay.save(update_fields=["provider_payment_id"])

        _log("webhook.mark_confirmed", {"pid": pid})
        return HttpResponse(status=204)

    # Desconocido o no soportado: log y 204 para no reintentar indefinidamente
    _log("webhook.unhandled_event", {"pid": pid, "event": event or "(none)"})
    return HttpResponse(status=204)

