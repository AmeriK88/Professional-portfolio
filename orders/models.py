# orders/models.py
from decimal import Decimal
from django.db import models
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.urls import reverse
from services.models import Service


def next_order_number():
    base = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"PO-{base}-{get_random_string(5).upper()}"


class Order(models.Model):
    PENDING   = "pending"
    AWAITING  = "awaiting_payment"
    PAID      = "paid"
    CANCELLED = "cancelled"
    REFUNDED  = "refunded"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (AWAITING, "Awaiting payment"),
        (PAID, "Paid"),
        (CANCELLED, "Cancelled"),
        (REFUNDED, "Refunded"),
    ]

    number     = models.CharField(max_length=32, unique=True, default=next_order_number, editable=False)
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    subtotal   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency   = models.CharField(max_length=10, default="EUR")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at    = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.number

    def recalc(self):
        from .models import OrderItem
        expr = ExpressionWrapper(
            F("unit_price") * F("quantity"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        s = OrderItem.objects.filter(order=self).aggregate(total=Sum(expr))["total"] or Decimal("0")
        self.subtotal = s
        self.total = s
        self.save(update_fields=["subtotal", "total"])

    def get_absolute_url(self):
        try:
            return reverse("orders:detail", args=[self.number])
        except Exception:
            return f"/orders/{self.number}/"


class OrderItem(models.Model):
    order      = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    service    = models.ForeignKey(Service, on_delete=models.PROTECT)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity   = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.service} x{self.quantity} ({self.order})"
