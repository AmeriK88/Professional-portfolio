import secrets
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from services.models import Service
from .models import Order, OrderItem, Payment
from django.db.models import Prefetch
from django.core.paginator import Paginator


@login_required
def checkout_service(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)

    # 1) crea pedido en EUR como ya haces
    order = Order.objects.create(user=request.user, status=Order.AWAITING, currency="EUR")
    OrderItem.objects.create(order=order, service=service, unit_price=service.price, quantity=1)
    order.recalc()  # deja total/subtotal en €

    # 2) ratio EUR por π
    eur_per_pi = getattr(settings, "PI_EUR_PER_PI", Decimal("0"))
    if eur_per_pi <= 0:
        return JsonResponse({"ok": False, "error": "PI_EUR_PER_PI not configured"}, status=500)

    # 3) calcula amount en π con 4 decimales
    amount_eur = Decimal(str(order.total))
    amount_pi  = (amount_eur / eur_per_pi).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    # 4) pago "initiated" con nonce
    nonce = secrets.token_hex(16)
    payment = Payment.objects.create(
        order=order,
        nonce=nonce,
        amount=amount_eur,     # seguimos guardando el € aquí (tu modelo actual)
        currency=order.currency # "EUR"
    )
    # Guarda también la conversión para auditoría
    payment.raw_payload = {
        "pricing": {
            "price_eur": str(amount_eur),
            "eur_per_pi": str(eur_per_pi),
            "amount_pi": str(amount_pi),
        }
    }
    payment.save(update_fields=["raw_payload"])

    # 5) payload para Pi SDK: ¡IMPORTANTE! 'amount' es en π
    payload = {
        "amount": float(amount_pi),  # π, no €
        "memo": f"Pedido {order.number} - {service.title}",
        "metadata": {
            "order_number": order.number,
            "service_slug": service.slug,
            "nonce": nonce,
            "price_eur": str(amount_eur),
            "eur_per_pi": str(eur_per_pi),
            "amount_pi": str(amount_pi),
        },
        # No poner "currency" aquí: Pi cobra siempre en π y ese campo no aplica
    }

    return JsonResponse({"ok": True, "order_number": order.number, "payment": payload})


@login_required
def my_orders(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .select_related("payment")
        .prefetch_related(Prefetch("items", queryset=OrderItem.objects.select_related("service")))
        .order_by("-id")
    )
    return render(request, "orders/list.html", {"orders": orders})

@login_required
def order_detail(request, number):
    order = get_object_or_404(request.user.order_set, number=number)

    eur_per_pi = None
    try:
        eur_per_pi = (
            order.payment.raw_payload.get("pricing", {}).get("eur_per_pi")
            if order.payment and order.payment.raw_payload
            else None
        )
    except Exception:
        eur_per_pi = None

    if eur_per_pi is None:
        eur_per_pi = getattr(settings, "DEFAULT_EUR_PER_PI", Decimal("1"))

    return render(request, "orders/detail.html", {
        "order": order,
        "eur_per_pi": eur_per_pi,
    })


@login_required
def order_list(request):
    qs = Order.objects.filter(user=request.user).order_by('-id')

    # Paginación opcional (10 por página)
    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)

    return render(request, "orders/list.html", {
        "orders": orders,
        "is_paginated": orders.has_other_pages(),
        "page_obj": orders,
        "eur_per_pi": getattr(settings, "DEFAULT_EUR_PER_PI", None),  # ej: Decimal("0.10")
    })