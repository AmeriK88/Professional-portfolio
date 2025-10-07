from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from pi_payments.models import Payment
from .models import Thread, Message

def _safe_get_txid(payment: Payment) -> str | None:
    raw = payment.raw_payload or {}
    return raw.get("txid") or (raw.get("transaction") or {}).get("txid")

@receiver(post_save, sender=Payment)
def on_payment_confirmed_create_thread_message(sender, instance: Payment, created, **kwargs):
    # Solo cuando está confirmado
    if instance.status != Payment.CONFIRMED:
        return

    order = instance.order
    # Hilo para ese pedido (uno a uno)
    thread, _ = Thread.objects.get_or_create(
        order=order,
        defaults={
            "user": order.user,
            "subject": f"Pedido {order.number}",
            "last_message_at": timezone.now(),
        },
    )

    # Idempotencia por txid (o por “marca” si no hay txid)
    txid = _safe_get_txid(instance)
    body = f"Pago confirmado para el pedido {order.number}."
    if txid:
        body = f"{body} TXID: {txid}"

    # Si ya existe un mensaje de sistema con ese txid (o mismo cuerpo), no duplicamos
    exists = Message.objects.filter(
        thread=thread,
        sender_type=Message.SENDER_SYSTEM,
        body__icontains=(txid or body) 
    ).exists()
    if exists:
        return

    Message.objects.create(
        thread=thread,
        sender_type=Message.SENDER_SYSTEM,
        body=body,
    )
