from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Order


class MyOrdersPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.owner = user_model.objects.create_user(
            username="orders_owner",
            password="test-password",
        )
        cls.other_user = user_model.objects.create_user(
            username="orders_other",
            password="test-password",
        )
        cls.owner_orders = [
            Order.objects.create(user=cls.owner)
            for _ in range(12)
        ]
        cls.other_order = Order.objects.create(user=cls.other_user)

    def setUp(self):
        self.client.force_login(self.owner)

    def test_orders_are_paginated_in_existing_descending_order(self):
        response = self.client.get(reverse("orders:list"), {"page": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["orders"]), 10)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(
            list(response.context["orders"].object_list),
            list(reversed(self.owner_orders[-10:])),
        )

        second_page = self.client.get(reverse("orders:list"), {"page": 2})
        self.assertEqual(len(second_page.context["orders"]), 2)
        self.assertEqual(
            list(second_page.context["orders"].object_list),
            list(reversed(self.owner_orders[:2])),
        )
        self.assertNotIn(self.other_order, second_page.context["orders"])

    def test_invalid_page_parameter_returns_first_page(self):
        response = self.client.get(
            reverse("orders:list"),
            {"page": "not-a-page"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(len(response.context["orders"]), 10)

    def test_out_of_range_page_returns_last_page(self):
        response = self.client.get(reverse("orders:list"), {"page": 999})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["orders"]), 2)

    def test_empty_order_list_renders_without_pagination(self):
        self.owner.order_set.all().delete()

        response = self.client.get(reverse("orders:list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["orders"]), 0)
        self.assertFalse(response.context["is_paginated"])
        self.assertContains(response, "Aún no tienes pedidos.")

    def test_list_only_contains_the_authenticated_users_orders(self):
        response = self.client.get(reverse("orders:list"))
        listed_orders = list(response.context["orders"].object_list)

        self.assertEqual(len(listed_orders), 10)
        self.assertNotIn(self.other_order, listed_orders)
        self.assertTrue(all(order.user_id == self.owner.id for order in listed_orders))

    def test_terminal_order_states_are_not_shown_as_completed_progress(self):
        for status, label in (
            (Order.CANCELLED, "Cancelado"),
            (Order.REFUNDED, "Reembolsado"),
        ):
            order = Order.objects.create(user=self.owner, status=status)
            response = self.client.get(
                reverse("orders:detail", args=[order.number])
            )

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, label)
            self.assertNotContains(response, 'role="progressbar"')
