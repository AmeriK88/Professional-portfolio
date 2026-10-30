from django.db import models
from django.utils import timezone
from django.db import transaction


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

    @transaction.atomic
    def mark_confirmed(self, tx_time=None, save_order=True):
        """
        Confirma un pago únicamente si su estado y el del pedido
        permiten la transición.

        Debe llamarse dentro de una transacción que bloquee
        primero Order y después Payment.
        """
        from orders.models import Order

        if self.status == self.CONFIRMED:
            return

        if self.status != self.INITIATED:
            raise ValueError(
                "Cannot confirm a payment that is not initiated"
            )

        if not save_order:
            raise ValueError(
                "Payment confirmation requires order synchronization"
            )

        order = self.order

        if order.status != Order.AWAITING:
            raise ValueError(
                "Cannot confirm payment: order is not awaiting payment"
            )

        self.status = self.CONFIRMED
        self.completed_at = tx_time or timezone.now()
        self.save(update_fields=["status", "completed_at"])

        order.status = Order.PAID
        order.paid_at = order.paid_at or self.completed_at
        order.save(update_fields=["status", "paid_at"])


    def mark_failed(self, reason: str | None = None, save_order: bool = True):
        if self.status == self.CONFIRMED:
            return
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
