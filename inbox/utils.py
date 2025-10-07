from django.utils import timezone
from .models import Thread, Message

def get_or_create_thread(order) -> Thread:
    thread = getattr(order, "inbox_thread", None)
    if thread:
        return thread
    subject = f"Pedido {order.number}"
    return Thread.objects.create(user=order.user, order=order, subject=subject, last_message_at=timezone.now())

def post_system_message(order, text: str) -> Message:
    thread = get_or_create_thread(order)
    return Message.objects.create(
        thread=thread,
        sender_type=Message.SENDER_SYSTEM,
        sender_user=None,
        body=text,
    )
