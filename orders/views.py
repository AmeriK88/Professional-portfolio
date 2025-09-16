import secrets
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from services.models import Service
from .models import Order, OrderItem, Payment

@login_required
def checkout_service(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)

    # 1) crea pedido
    order = Order.objects.create(user=request.user, status=Order.AWAITING, currency="EUR")
    OrderItem.objects.create(order=order, service=service, unit_price=service.price, quantity=1)
    order.recalc()

    # 2) crea pago "initiated" con nonce (idempotencia)
    nonce = secrets.token_hex(16)
    payment = Payment.objects.create(order=order, nonce=nonce, amount=order.total, currency=order.currency)

    # 3) Devolvemos datos que usarás en el Pi SDK del frontend
    #    IMPORTANTE: metadata es clave para atar el pid → order.number y nuestro nonce
    payload = {
        "amount": str(order.total),
        "currency": order.currency,
        "memo": f"Pedido {order.number} - {service.title}",
        "metadata": {
            "order_number": order.number,
            "service_slug": service.slug,
            "nonce": nonce,
        },
    }
    return JsonResponse({"ok": True, "order_number": order.number, "payment": payload})
