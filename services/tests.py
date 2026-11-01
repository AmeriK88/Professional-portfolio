from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from orders.models import Order
from pi_payments.models import Payment
from .models import Service


class PaymentReceiptAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.owner = user_model.objects.create_user(
            username="receipt_owner",
            password="test-password",
        )
        cls.other_user = user_model.objects.create_user(
            username="receipt_other",
            password="test-password",
        )
        cls.order = Order.objects.create(user=cls.owner, status=Order.PAID)
        cls.payment = Payment.objects.create(
            order=cls.order,
            provider_payment_id="pi_receipt_private_id",
            status=Payment.CONFIRMED,
            nonce=uuid4().hex,
            raw_payload={"txid": "private-txid"},
        )

    def test_owner_can_view_payment_receipt(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("services:payment_success"),
            {"pid": self.payment.provider_payment_id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["order"], self.order)
        self.assertEqual(response.context["payment"], self.payment)
        self.assertContains(response, self.payment.provider_payment_id)

    def test_another_user_cannot_view_receipt_by_payment_id(self):
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse("services:payment_success"),
            {"pid": self.payment.provider_payment_id},
        )
        invalid_response = self.client.get(
            reverse("services:payment_success"),
            {"pid": "pi_invalid_unmatched_id"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["order"])
        self.assertIsNone(response.context["payment"])
        self.assertIsNone(response.context["payment_id"])
        self.assertNotContains(response, self.payment.provider_payment_id)
        self.assertNotContains(response, self.order.number)
        self.assertEqual(invalid_response.status_code, response.status_code)
        self.assertIsNone(invalid_response.context["order"])
        self.assertIsNone(invalid_response.context["payment"])
        self.assertIsNone(invalid_response.context["payment_id"])

    def test_unauthenticated_user_is_redirected_to_login(self):
        response = self.client.get(
            reverse("services:payment_success"),
            {"pid": self.payment.provider_payment_id},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response["Location"])
        self.assertNotEqual(response.status_code, 200)

    def test_invalid_payment_id_does_not_fall_back_to_latest_order(self):
        self.client.force_login(self.owner)
        invalid_pid = "pi_invalid_unmatched_id"

        response = self.client.get(
            reverse("services:payment_success"),
            {"pid": invalid_pid},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["order"])
        self.assertIsNone(response.context["payment"])
        self.assertIsNone(response.context["payment_id"])
        self.assertNotContains(response, invalid_pid)
        self.assertNotContains(response, self.order.number)

    def test_receipt_without_payment_id_keeps_owner_order_fallback(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("services:payment_success"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["order"], self.order)
        self.assertEqual(response.context["payment"], self.payment)


class PiSandboxConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.service = Service.objects.create(
            title="Sandbox configuration test",
            description="Test service",
            price=Decimal("1.00"),
        )

    @override_settings(PI_SANDBOX=True)
    def test_sandbox_setting_is_rendered_into_shared_pi_config(self):
        response = self.client.get(
            reverse("services:detail", args=[self.service.slug])
        )

        self.assertContains(response, "sandbox: true")
        self.assertContains(response, "approveUrl:")
        self.assertContains(response, "completeUrl:")
        self.assertContains(response, "cancelUrl:")

    @override_settings(PI_SANDBOX=False)
    def test_live_setting_is_rendered_into_shared_pi_config(self):
        response = self.client.get(
            reverse("services:detail", args=[self.service.slug])
        )

        self.assertContains(response, "sandbox: false")
