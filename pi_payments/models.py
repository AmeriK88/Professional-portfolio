from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class Payment(models.Model):
    INITIATED = "initiated"
    CONFIRMED = "confirmed"
    FAILED    = "failed"
    STATUS_CHOICES = [
        (INITIATED, "Initiated"),
        (CONFIRMED, "Confirmed"),
        (FAILED,    "Failed"),
    ]

    order               = models.OneToOneField("orders.Order", related_name="payment", on_delete=models.CASCADE)
    provider            = models.CharField(max_length=30, default="pi")
    provider_payment_id = models.CharField(max_length=100, unique=True, null=True, blank=True)

    status              = models.CharField(max_length=20, choices=STATUS_CHOICES, default=INITIATED)
    amount              = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency            = models.CharField(max_length=10, default="EUR")
    nonce               = models.CharField(max_length=64, unique=True)

    raw_payload         = models.JSONField(default=dict, blank=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    completed_at        = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Payment({self.provider} · {self.provider_payment_id or '-'})"

    def mark_confirmed(self, tx_time=None, save_order=True):
        self.status = self.CONFIRMED
        self.completed_at = tx_time or timezone.now()
        self.save(update_fields=["status", "completed_at"])
        if save_order:
            o = self.order
            if getattr(o, "status", None) != getattr(o, "PAID", "paid"):
                o.status = getattr(o, "PAID", "paid")
                o.paid_at = o.paid_at or self.completed_at
                o.save(update_fields=["status", "paid_at"])

    def mark_failed(self, reason: str | None = None, save_order: bool = True):
        raw = self.raw_payload or {}
        if reason:
            raw.setdefault("fail_reasons", []).append(
                {"reason": reason, "at": timezone.now().isoformat()}
            )
        self.raw_payload = raw
        self.status = self.FAILED
        self.completed_at = None
        self.save(update_fields=["status", "raw_payload", "completed_at"])

        if save_order:
            o = self.order
            # Solo cancela si aún no está pagado
            if o.status not in (getattr(o, "PAID", "paid"),):
                o.status = getattr(o, "CANCELLED", "cancelled")
                o.paid_at = None
                o.save(update_fields=["status", "paid_at"])


@receiver(post_save, sender=Payment)
def _sync_order_status_on_payment(sender, instance: Payment, **kwargs):
    if instance.status == Payment.CONFIRMED:
        o = instance.order
        if o.status != getattr(o, "PAID", "paid"):
            o.status = getattr(o, "PAID", "paid")
            o.paid_at = o.paid_at or (instance.completed_at or timezone.now())
            o.save(update_fields=["status", "paid_at"])
