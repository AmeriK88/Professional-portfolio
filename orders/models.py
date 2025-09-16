from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from services.models import Service

def next_order_number():
    base = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"PO-{base}-{get_random_string(5).upper()}"

class Order(models.Model):
    PENDING = "pending"
    AWAITING = "awaiting_payment"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (AWAITING, "Awaiting payment"),
        (PAID, "Paid"),
        (CANCELLED, "Cancelled"),
        (REFUNDED, "Refunded"),
    ]

    number    = models.CharField(max_length=32, unique=True, default=next_order_number, editable=False)
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status    = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    subtotal  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency  = models.CharField(max_length=10, default="EUR")
    created_at= models.DateTimeField(auto_now_add=True)
    paid_at   = models.DateTimeField(null=True, blank=True)

    def recalc(self):
        s = sum((i.unit_price * i.quantity for i in self.items.all()), Decimal("0"))
        self.subtotal = s
        self.total = s  # aquí luego aplicas impuestos/descuentos si quieres
        self.save(update_fields=["subtotal", "total"])

class OrderItem(models.Model):
    order      = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    service    = models.ForeignKey(Service, on_delete=models.PROTECT)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity   = models.PositiveIntegerField(default=1)

class Payment(models.Model):
    INITIATED = "initiated"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    STATUS_CHOICES = [
        (INITIATED, "Initiated"),
        (CONFIRMED, "Confirmed"),
        (FAILED, "Failed"),
    ]

    order                = models.OneToOneField(Order, related_name="payment", on_delete=models.CASCADE)
    provider             = models.CharField(max_length=30, default="pi")
    provider_payment_id  = models.CharField(max_length=100, unique=True, null=True, blank=True)  # pid
    status               = models.CharField(max_length=20, choices=STATUS_CHOICES, default=INITIATED)
    amount               = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency             = models.CharField(max_length=10, default="EUR")
    nonce                = models.CharField(max_length=64, unique=True)  # idempotencia
    raw_payload          = models.JSONField(default=dict, blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    completed_at         = models.DateTimeField(null=True, blank=True)
