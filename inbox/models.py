from django.conf import settings
from django.db import models
from django.utils import timezone

class Thread(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inbox_threads")
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="inbox_thread")
    subject = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-last_message_at", "-updated_at", "-id")

    def __str__(self) -> str:
        return self.subject or f"Inbox · Pedido {self.order.number}"

    def touch(self, when=None):
        self.last_message_at = when or timezone.now()
        self.save(update_fields=["last_message_at", "updated_at"])


class Message(models.Model):
    SENDER_SYSTEM = "system"
    SENDER_USER   = "user"
    SENDER_ADMIN  = "admin"
    SENDER_CHOICES = [
        (SENDER_SYSTEM, "System"),
        (SENDER_USER,   "User"),
        (SENDER_ADMIN,  "Admin"),
    ]

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=12, choices=SENDER_CHOICES, default=SENDER_SYSTEM)
    sender_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="inbox_messages")
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.get_sender_type_display()} · {self.created_at:%Y-%m-%d %H:%M}"  # type: ignore[attr-defined]


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Usa el objeto relacionado directamente; nada de pk=self.thread_id
        self.thread.touch(self.created_at)
