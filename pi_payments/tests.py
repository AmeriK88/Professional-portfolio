
import json
from unittest.mock import Mock, patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from orders.models import Order
from pi_payments.models import Payment


class PaymentStateTransitionTests(TestCase):
    """Pruebas de integridad de pagos y pedidos."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="pi_test_user",
            password="TestPassword123!",
        )

    def create_payment(self, payment_status=None, order_status=None):
        order = Order.objects.create(
            user=self.user,
            status=order_status or Order.AWAITING,
        )

        payment = Payment.objects.create(
            order=order,
            provider="pi",
            status=payment_status or Payment.INITIATED,
            nonce=uuid4().hex,
        )

        return payment, order

    def test_initiated_payment_can_be_cancelled(self):
        payment, order = self.create_payment()

        payment.mark_failed(reason="pi_cancel_verified")

        payment.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(payment.status, Payment.FAILED)
        self.assertEqual(order.status, Order.CANCELLED)
        self.assertIsNone(payment.completed_at)
        self.assertIsNone(order.paid_at)

        self.assertEqual(
            payment.raw_payload["fail_reasons"][0]["reason"],
            "pi_cancel_verified",
        )

    def test_confirmed_payment_cannot_be_cancelled(self):
        payment, order = self.create_payment(
            payment_status=Payment.CONFIRMED,
            order_status=Order.PAID,
        )

        with self.assertRaises(ValueError):
            payment.mark_failed(reason="invalid_cancel")

        payment.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(payment.status, Payment.CONFIRMED)
        self.assertEqual(order.status, Order.PAID)

    def test_paid_order_cannot_be_cancelled(self):
        payment, order = self.create_payment(
            payment_status=Payment.INITIATED,
            order_status=Order.PAID,
        )

        with self.assertRaises(ValueError):
            payment.mark_failed(reason="invalid_cancel")

        payment.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(payment.status, Payment.INITIATED)
        self.assertEqual(order.status, Order.PAID)
        self.assertEqual(payment.raw_payload, {})

    def test_repeated_cancellation_is_idempotent(self):
        payment, order = self.create_payment()

        payment.mark_failed(reason="pi_cancel_verified")
        payment.refresh_from_db()

        original_payload = payment.raw_payload.copy()

        payment.mark_failed(reason="duplicate_cancel")

        payment.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(payment.status, Payment.FAILED)
        self.assertEqual(order.status, Order.CANCELLED)
        self.assertEqual(payment.raw_payload, original_payload)
        self.assertEqual(len(payment.raw_payload["fail_reasons"]), 1)

    def test_failed_transition_does_not_change_database(self):
        payment, order = self.create_payment(
            order_status=Order.REFUNDED,
        )

        with self.assertRaises(ValueError):
            payment.mark_failed(reason="invalid_transition")

        payment.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(payment.status, Payment.INITIATED)
        self.assertEqual(order.status, Order.REFUNDED)
        self.assertEqual(payment.raw_payload, {})

    def test_confirmed_payment_marks_order_paid(self):
        payment, order = self.create_payment()

        payment.mark_confirmed(tx_time=timezone.now())

        payment.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(payment.status, Payment.CONFIRMED)
        self.assertEqual(order.status, Order.PAID)
        self.assertIsNotNone(payment.completed_at)
        self.assertIsNotNone(order.paid_at)


class PiCompleteViewTests(TestCase):
    """Pruebas HTTP del flujo de confirmación de Pi Network."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="pi_complete_user",
            password="TestPassword123!",
        )

    def setUp(self):
        self.client.force_login(self.user)

        self.order = Order.objects.create(
            user=self.user,
            status=Order.AWAITING,
        )

        self.pid = f"pi_test_{uuid4().hex}"
        self.txid = f"tx_test_{uuid4().hex}"
        self.nonce = uuid4().hex

        self.payment = Payment.objects.create(
            order=self.order,
            provider="pi",
            provider_payment_id=self.pid,
            status=Payment.INITIATED,
            nonce=self.nonce,
            raw_payload={
                "pricing": {
                    "amount_pi": "2.50",
                }
            },
        )

    @patch("pi_payments.views.requests.post")
    @patch("pi_payments.views._fetch_pi_payment")
    def test_valid_pi_payment_confirms_order(
        self,
        mock_fetch,
        mock_post,
    ):
        """Un pago válido confirma Payment y marca Order como pagado."""

        # Primera consulta a Pi Network.
        initial_info = {
            "identifier": self.pid,
            "amount": "2.50",
            "metadata": {
                "order_number": self.order.number,
                "nonce": self.nonce,
            },
        }

        # Segunda consulta, tras completar el pago.
        final_info = {
            **initial_info,
            "transaction": {
                "txid": self.txid,
            },
            "status": {
                "developer_completed": True,
            },
        }

        # Simulamos ambas consultas sin acceder a Pi Network.
        mock_fetch.side_effect = [
            (Mock(ok=True), initial_info),
            (Mock(ok=True), final_info),
        ]

        # Simulamos la respuesta de /complete.
        mock_post.return_value = Mock(
            ok=True,
            status_code=200,
        )

        response = self.client.post(
            reverse("pi:complete"),
            data=json.dumps({
                "paymentId": self.pid,
                "txid": self.txid,
            }),
            content_type="application/json",
        )

        # La API debe responder correctamente.
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        # Consultamos los valores reales guardados en la BD.
        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        # El pago debe estar confirmado.
        self.assertEqual(
            self.payment.status,
            Payment.CONFIRMED,
        )

        # El pedido debe estar pagado.
        self.assertEqual(
            self.order.status,
            Order.PAID,
        )

        # Deben existir fechas de confirmación.
        self.assertIsNotNone(self.payment.completed_at)
        self.assertIsNotNone(self.order.paid_at)

        # Se debe conservar el identificador de la transacción.
        self.assertEqual(
            self.payment.raw_payload["txid"],
            self.txid,
        )

        # Deben realizarse dos verificaciones y una finalización.
        self.assertEqual(mock_fetch.call_count, 2)
        mock_post.assert_called_once()
