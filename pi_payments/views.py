import os, json, requests
from decimal import Decimal
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

from orders.models import Order
from pi_payments.models import Payment
from django.contrib.auth.decorators import login_required
from django.db import transaction

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


@login_required
@require_POST
def pi_approve(request):
    data = _json(request.body)
    pid = data.get("paymentId")

    if not isinstance(pid, str) or not pid.strip():
        return HttpResponseBadRequest("paymentId required")

    # 1) Consulta el pago directamente en Pi Network.
    # Nunca utilizamos los metadatos enviados por el navegador
    # para identificar o autorizar un pedido.
    try:
        r_info, info = _fetch_pi_payment(pid)
    except requests.RequestException:
        _log("approve.fetch_error", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment verification unavailable"},
            status=502,
        )

    if not r_info.ok or not isinstance(info, dict):
        _log(
            "approve.fetch_fail",
            {"pid": pid, "status": r_info.status_code},
        )
        return JsonResponse(
            {"ok": False, "error": "cannot verify payment"},
            status=502,
        )

    # 2) Comprueba que Pi devuelve el identificador solicitado.
    if str(info.get("identifier", "")) != pid:
        _log("approve.identifier_mismatch", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment identifier mismatch"},
            status=400,
        )

    # 3) Obtiene los metadatos verificados desde Pi Network.
    metadata = info.get("metadata")

    if not isinstance(metadata, dict):
        return JsonResponse(
            {"ok": False, "error": "invalid payment metadata"},
            status=400,
        )

    order_number = metadata.get("order_number")
    nonce = metadata.get("nonce")

    if not order_number or not nonce:
        return JsonResponse(
            {"ok": False, "error": "missing payment metadata"},
            status=400,
        )

    # 4) Busca exclusivamente un pago perteneciente al usuario.
    # También exige que el nonce coincida con el generado en checkout.
    pay = (
        Payment.objects
        .select_related("order")
        .filter(
            order__number=order_number,
            order__user=request.user,
            nonce=nonce,
            provider="pi",
        )
        .first()
    )

    if not pay:
        return JsonResponse(
            {"ok": False, "error": "payment not found"},
            status=404,
        )

    # 5) Evita asociar un pago externo diferente al mismo pedido.
    if pay.provider_payment_id and pay.provider_payment_id != pid:
        _log("approve.provider_mismatch", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment already linked"},
            status=409,
        )

    # Nunca reiniciamos un pago confirmado.
    if pay.status == Payment.CONFIRMED:
        return JsonResponse(
            {"ok": True, "already_confirmed": True},
        )

    # Solo aprobamos pedidos que siguen esperando el pago.
    if pay.order.status != Order.AWAITING:
        return JsonResponse(
            {"ok": False, "error": "order is not awaiting payment"},
            status=409,
        )

    if pay.status != Payment.INITIATED:
        return JsonResponse(
            {"ok": False, "error": "payment is not initiated"},
            status=409,
        )

    # 6) Valida obligatoriamente el importe contra el snapshot
    # generado por Django durante el checkout.
    try:
        amount_pi = Decimal(str(info["amount"]))
        pricing = (pay.raw_payload or {})["pricing"]
        expected_pi = Decimal(str(pricing["amount_pi"]))

        if (
            not amount_pi.is_finite()
            or not expected_pi.is_finite()
            or amount_pi <= 0
            or expected_pi <= 0
            or amount_pi != expected_pi
        ):
            raise ValueError("Invalid or mismatched amount")

    except (KeyError, TypeError, ValueError, ArithmeticError):
        _log("approve.amount_mismatch", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment amount mismatch"},
            status=400,
        )

    # 7) Solicita la aprobación a Pi Network únicamente después
    # de superar las comprobaciones de identidad y precio.
    try:
        r = requests.post(
            f"{PI_API_BASE}/v2/payments/{pid}/approve",
            headers=_auth_headers(),
            timeout=20,
        )
    except requests.RequestException:
        _log("approve.api_error", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment approval unavailable"},
            status=502,
        )

    _log(
        "approve.api",
        {"pid": pid, "status": r.status_code},
    )

    if not r.ok:
        # No cancelamos automáticamente el pedido ante un error.
        # Una respuesta fallida no demuestra que el pago sea inválido.
        return JsonResponse(
            {"ok": False, "error": "payment approval failed"},
            status=502,
        )

    # 8) Vincula el identificador externo solo tras la aprobación.
    # Conserva los metadatos de pricing y el historial existente.
    raw = dict(pay.raw_payload or {})
    raw["pi_info_at_approve"] = info

    # La actualización condicional evita sobrescribir otro
    # identificador de Pi que se haya vinculado entretanto.
    updated = (
        Payment.objects
        .filter(
            pk=pay.pk,
            provider_payment_id__isnull=True,
            status=Payment.INITIATED,
        )
        .update(
            provider_payment_id=pid,
            raw_payload=raw,
        )
    )

    if not updated:
        # Una repetición del callback puede encontrar el mismo
        # identificador ya vinculado. No lo tratamos como otro pago.
        already_linked = Payment.objects.filter(
            pk=pay.pk,
            provider_payment_id=pid,
            status=Payment.INITIATED,
        ).exists()

        if not already_linked:
            return JsonResponse(
                {"ok": False, "error": "payment link conflict"},
                status=409,
            )

    _log(
        "approve.local_linked",
        {"pid": pid, "order": pay.order.number},
    )

    return JsonResponse({"ok": True})



@login_required
@require_POST
def pi_complete(request):
    data = _json(request.body)
    pid = data.get("paymentId")
    txid = data.get("txid")

    if not pid or not txid:
        return HttpResponseBadRequest("paymentId and txid required")

    # 1) Busca el pago local y comprueba que pertenece al usuario autenticado.
    # No modificamos ningún registro antes de verificar la autorización.
    pay = (
        Payment.objects
        .select_related("order")
        .filter(
            provider_payment_id=pid,
            order__user=request.user,
        )
        .first()
    )

    if not pay:
        return JsonResponse(
            {"ok": False, "error": "payment not found"},
            status=404,
        )

    # Idempotencia: un pago confirmado no debe procesarse de nuevo.
    if pay.status == Payment.CONFIRMED:
        return JsonResponse({"ok": True, "already_confirmed": True})

    # 2) Consulta la información del pago directamente en Pi Network.
    # Nunca debemos confiar únicamente en los datos enviados por el navegador.
    try:
        r_info, info = _fetch_pi_payment(pid)
    except requests.RequestException:
        _log("complete.fetch_error", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment verification unavailable"},
            status=502,
        )

    if not r_info.ok or not isinstance(info, dict):
        _log(
            "complete.fetch_fail",
            {"pid": pid, "status": r_info.status_code},
        )
        # Un error de comunicación no implica que el pago haya fallado.
        return JsonResponse(
            {"ok": False, "error": "cannot verify payment"},
            status=502,
        )

    # 3) Comprueba que Pi Network devuelve el mismo identificador.
    if str(info.get("identifier", "")) != str(pid):
        _log("complete.identifier_mismatch", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment identifier mismatch"},
            status=400,
        )

    # 4) Validación obligatoria del importe en Pi contra el snapshot
    # generado durante el checkout. Si falta información, bloqueamos.
    try:
        amount_pi = Decimal(str(info["amount"]))
        snap = (pay.raw_payload or {})["pricing"]
        snap_amount_pi = Decimal(str(snap["amount_pi"]))

        if (
            not amount_pi.is_finite()
            or not snap_amount_pi.is_finite()
            or amount_pi <= 0
            or snap_amount_pi <= 0
            or amount_pi != snap_amount_pi
        ):
            raise ValueError("Invalid or mismatched amount")

    except (KeyError, TypeError, ValueError, ArithmeticError):
        _log("complete.amount_invalid", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment amount mismatch"},
            status=400,
        )

    # 5) Comprueba que los metadatos corresponden
    # exactamente al pedido y al pago local.
    metadata = info.get("metadata")

    if (
        not isinstance(metadata, dict)
        or str(metadata.get("order_number", "")) != pay.order.number
        or str(metadata.get("nonce", "")) != pay.nonce
    ):
        _log("complete.metadata_mismatch", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment metadata mismatch"},
            status=400,
        )

    # 6) Solicita a Pi Network que complete la transacción.
    try:
        r = requests.post(
            f"{PI_API_BASE}/v2/payments/{pid}/complete",
            headers=_auth_headers(),
            json={"txid": txid},
            timeout=20,
        )
    except requests.RequestException:
        _log("complete.api_error", {"pid": pid})
        return JsonResponse(
            {"ok": False, "error": "payment completion unavailable"},
            status=502,
        )

    _log(
        "complete.api",
        {"pid": pid, "status": r.status_code},
    )

    if not r.ok:
        # No marcamos el pago como fallido automáticamente.
        # Podría haberse completado y haberse perdido la respuesta.
        return JsonResponse(
            {"ok": False, "error": "payment completion not verified"},
            status=502,
        )

    # 7) Vuelve a consultar Pi Network para verificar el estado final.
    try:
        r_final, final_info = _fetch_pi_payment(pid)
    except requests.RequestException:
        return JsonResponse(
            {"ok": False, "error": "final verification unavailable"},
            status=502,
        )

    if not r_final.ok or not isinstance(final_info, dict):
        return JsonResponse(
            {"ok": False, "error": "final verification failed"},
            status=502,
        )

    pi_transaction = final_info.get("transaction") or {}
    final_txid = (
        pi_transaction.get("txid")
        if isinstance(pi_transaction, dict)
        else None
    )

    if (
        str(final_info.get("identifier", "")) != str(pid)
        or str(final_txid or "") != str(txid)
    ):
        return JsonResponse(
            {"ok": False, "error": "transaction verification failed"},
            status=400,
        )

    # Pi debe confirmar explícitamente la finalización.
    status_info = final_info.get("status")

    if (
        not isinstance(status_info, dict)
        or status_info.get("developer_completed") is not True
    ):
        return JsonResponse(
            {"ok": False, "error": "payment not confirmed by Pi"},
            status=409,
        )
    # 7.1) Revalida el importe y los metadatos finales de Pi.
    try:
        final_amount = Decimal(str(final_info["amount"]))
        expected_amount = Decimal(
            str((pay.raw_payload or {})["pricing"]["amount_pi"])
        )

        if (
            not final_amount.is_finite()
            or not expected_amount.is_finite()
            or final_amount <= 0
            or expected_amount <= 0
            or final_amount != expected_amount
        ):
            raise ValueError("Final payment amount mismatch")

    except (KeyError, TypeError, ValueError, ArithmeticError):
        return JsonResponse(
            {"ok": False, "error": "final payment amount mismatch"},
            status=400,
        )

    final_metadata = final_info.get("metadata")

    if (
        not isinstance(final_metadata, dict)
        or str(final_metadata.get("order_number", "")) != pay.order.number
        or str(final_metadata.get("nonce", "")) != pay.nonce
    ):
        return JsonResponse(
            {"ok": False, "error": "final payment metadata mismatch"},
            status=400,
        )
    
    # 8) Confirma el pago y el pedido dentro de una transacción.
    # Adquirimos los bloqueos en el mismo orden que pi_cancel():
    # primero Order y después Payment.

    with transaction.atomic():
        order = (
            Order.objects
            .select_for_update()
            .get(pk=pay.order_id)
        )

        locked_pay = (
            Payment.objects
            .select_for_update()
            .get(pk=pay.pk)
        )

        # Si otro proceso ya confirmó el pago, no repetimos la operación.
        if locked_pay.status == Payment.CONFIRMED:
            return JsonResponse({
                "ok": True,
                "already_confirmed": True,
            })

        # No confirmamos automáticamente un pago marcado como fallido.
        # Requiere reconciliación antes de cambiar su estado.
        if locked_pay.status != Payment.INITIATED:
            return JsonResponse(
                {"ok": False, "error": "payment is not initiated"},
                status=409,
            )

        # El pedido debe seguir esperando el pago.
        if order.status != Order.AWAITING:
            return JsonResponse(
                {"ok": False, "error": "order is not awaiting payment"},
                status=409,
            )

        # Comprueba que el identificador externo no haya cambiado
        # mientras verificábamos la operación con Pi.
        if locked_pay.provider_payment_id != pid:
            return JsonResponse(
                {"ok": False, "error": "payment identifier conflict"},
                status=409,
            )

        # Conserva el historial y registra la respuesta final de Pi.
        raw = dict(locked_pay.raw_payload or {})
        raw["pi_info_at_complete"] = final_info
        raw["txid"] = txid

        locked_pay.raw_payload = raw
        locked_pay.save(update_fields=["raw_payload"])

        # mark_confirmed() actualiza Payment y sincroniza Order.
        # Ambos cambios quedan protegidos por la transacción.
        locked_pay.mark_confirmed(save_order=True)


    _log(
        "complete.confirmed",
        {"pid": pid, "order": pay.order.number},
    )

    return JsonResponse({"ok": True})



@login_required
@require_POST
def pi_cancel(request):
    """
    Cancela un pago Pi perteneciente al usuario autenticado.

    La petición del navegador no es suficiente para demostrar
    que Pi ha cancelado realmente la operación.
    """

    data = _json(request.body)
    pid = data.get("paymentId")

    if not isinstance(pid, str) or not pid.strip():
        return HttpResponseBadRequest("paymentId required")

    # 1. Consulta el estado del pago en Pi Network.
    try:
        r_info, info = _fetch_pi_payment(pid)
    except requests.RequestException:
        return JsonResponse(
            {"ok": False, "error": "payment verification unavailable"},
            status=502,
        )

    if not r_info.ok or not isinstance(info, dict):
        return JsonResponse(
            {"ok": False, "error": "cannot verify payment"},
            status=502,
        )

    if str(info.get("identifier", "")) != pid:
        return JsonResponse(
            {"ok": False, "error": "payment identifier mismatch"},
            status=400,
        )

    # 2. Obtiene los metadatos desde Pi, no desde el navegador.
    metadata = info.get("metadata")

    if not isinstance(metadata, dict):
        return JsonResponse(
            {"ok": False, "error": "invalid payment metadata"},
            status=400,
        )

    order_number = metadata.get("order_number")
    nonce = metadata.get("nonce")

    if not order_number or not nonce:
        return JsonResponse(
            {"ok": False, "error": "missing payment metadata"},
            status=400,
        )

    # 3. Verifica que el pedido pertenece al usuario.
    pay = (
        Payment.objects
        .select_related("order")
        .filter(
            order__number=order_number,
            order__user=request.user,
            nonce=nonce,
        )
        .first()
    )

    if not pay:
        return JsonResponse(
            {"ok": False, "error": "payment not found"},
            status=404,
        )

    # No permitimos asociar otro pago externo al pedido.
    if pay.provider_payment_id not in (None, "", pid):
        return JsonResponse(
            {"ok": False, "error": "payment identifier conflict"},
            status=409,
        )

    # 4. Comprueba que el importe coincide con el checkout.
    try:
        amount_pi = Decimal(str(info["amount"]))
        pricing = (pay.raw_payload or {})["pricing"]
        expected_pi = Decimal(str(pricing["amount_pi"]))

        if (
            not amount_pi.is_finite()
            or not expected_pi.is_finite()
            or amount_pi <= 0
            or amount_pi != expected_pi
        ):
            raise ValueError("Invalid payment amount")

    except (KeyError, TypeError, ValueError, ArithmeticError):
        return JsonResponse(
            {"ok": False, "error": "payment amount mismatch"},
            status=400,
        )

    # 5. Nunca cancelamos una transacción completada.
    status_info = info.get("status")

    if not isinstance(status_info, dict):
        return JsonResponse(
            {"ok": False, "error": "invalid payment status"},
            status=400,
        )

    if status_info.get("developer_completed") is True:
        return JsonResponse(
            {"ok": False, "error": "payment already completed"},
            status=409,
        )

    # El callback onCancel del navegador no demuestra por sí solo
    # que el pago haya sido cancelado por Pi.
    if status_info.get("cancelled") is not True:
        return JsonResponse(
            {"ok": False, "error": "payment cancellation not verified"},
            status=409,
        )

    # 6. Bloquea el pedido y el pago durante la modificación.
    from django.db import transaction

    with transaction.atomic():
        order = (
            Order.objects
            .select_for_update()
            .get(pk=pay.order_id)
        )

        locked_pay = (
            Payment.objects
            .select_for_update()
            .get(pk=pay.pk)
        )

        # Revalidación tras adquirir los bloqueos.
        if (
            locked_pay.status == Payment.CONFIRMED
            or order.status == Order.PAID
        ):
            return JsonResponse(
                {"ok": False, "error": "payment already confirmed"},
                status=409,
            )

        if locked_pay.provider_payment_id not in (None, "", pid):
            return JsonResponse(
                {"ok": False, "error": "payment identifier conflict"},
                status=409,
            )

        if locked_pay.status == Payment.FAILED:
            return JsonResponse(
                {"ok": True, "already_cancelled": True}
            )

        # Conserva la información existente para auditoría.
        raw = dict(locked_pay.raw_payload or {})
        raw["pi_info_at_cancel"] = info
        locked_pay.raw_payload = raw
        locked_pay.save(update_fields=["raw_payload"])

        # mark_failed() actualiza el pago y cancela el pedido.
        locked_pay.mark_failed(
            reason="pi_cancel_verified",
            save_order=True,
        )

    _log(
        "cancel.verified",
        {"pid": pid, "order": order.number},
    )

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

