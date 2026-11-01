from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from pi_payments.models import Payment
from orders.models import Order
from .models import Service

def service_list(request):
    services = Service.objects.filter(is_active=True)
    return render(request, 'services/service_list.html', {'services': services})

@ensure_csrf_cookie
def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    return render(request, "services/service_detail.html", {"service": service})

@login_required
def payment_success(request):
    pid = request.GET.get("pid")
    payment = None
    order = None
    txid = None

    if pid:
        payment = (
            Payment.objects
            .select_related("order", "order__user")
            .filter(provider_payment_id=pid, order__user=request.user)
            .first()
        )
        if payment:
            order = payment.order
            txid = (payment.raw_payload or {}).get("txid")

    if not pid:
        order = (
            Order.objects
            .filter(user=request.user)
            .order_by("-id")
            .first()
        )
        if order:
            payment = getattr(order, "payment", None)
            if payment and not txid:
                txid = (payment.raw_payload or {}).get("txid")

    ctx = {
        "payment_id": payment.provider_payment_id if payment else None,
        "payment": payment,
        "order": order,
        "txid": txid,
    }
    return render(request, "services/payment_success.html", ctx)
