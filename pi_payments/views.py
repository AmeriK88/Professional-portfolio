# pi_payments/views.py
import os, json, requests
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now

PI_API_BASE = "https://api.minepi.com"
PI_API_KEY  = os.environ.get("PI_API_KEY")

def _auth_headers():
    return {"Authorization": f"Key {PI_API_KEY}", "Content-Type": "application/json"}

def _log(event, payload):  # cámbialo por logging si quieres
    print(f"[PI] {event} {now().isoformat()} :: {payload}")

@require_POST
def pi_approve(request):
    data = json.loads(request.body.decode())
    pid  = data.get("paymentId")
    if not pid:
        return HttpResponseBadRequest("paymentId required")
    r = requests.post(f"{PI_API_BASE}/v2/payments/{pid}/approve", headers=_auth_headers(), timeout=20)
    _log("approve", {"pid": pid, "status": r.status_code, "body": r.text})
    return JsonResponse({"ok": r.ok})

@require_POST
def pi_complete(request):
    data = json.loads(request.body.decode())
    pid  = data.get("paymentId")
    txid = data.get("txid")
    if not pid or not txid:
        return HttpResponseBadRequest("paymentId and txid required")
    r = requests.post(f"{PI_API_BASE}/v2/payments/{pid}/complete",
                      headers=_auth_headers(), json={"txid": txid}, timeout=20)
    _log("complete", {"pid": pid, "status": r.status_code, "body": r.text})
    if not r.ok:
        return JsonResponse({"ok": False}, status=400)
    # TODO: Marca tu pedido/servicio como pagado aquí
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
