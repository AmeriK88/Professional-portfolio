from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from orders.models import Order


User = get_user_model()


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-owner",
            email="owner@example.com",
            password="test-password-123",
            first_name="Profile",
            last_name="Owner",
        )
        self.other_user = User.objects.create_user(
            username="another-account",
            email="another@example.com",
            password="test-password-456",
        )
        self.profile_url = reverse("users:profile")
        self.client.force_login(self.user)

    def test_profile_requires_authentication(self):
        self.client.logout()

        response = self.client.get(self.profile_url)

        self.assertRedirects(
            response,
            f"{reverse('users:login')}?next={self.profile_url}",
        )

    def test_profile_displays_only_authenticated_users_information_and_orders(self):
        own_order = Order.objects.create(user=self.user, number="PO-OWNER-001")
        other_order = Order.objects.create(user=self.other_user, number="PO-OTHER-001")

        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user.username)
        self.assertContains(response, self.user.email)
        self.assertContains(response, "Alta")
        self.assertContains(response, "Último acceso")
        self.assertContains(response, "Total de pedidos:")
        self.assertEqual(response.context["orders_count"], 1)
        self.assertEqual(response.context["last_order"], own_order)
        self.assertContains(response, own_order.pk)
        self.assertNotContains(response, other_order.number)
        self.assertNotContains(response, self.other_user.username)

    def test_profile_contains_existing_account_navigation(self):
        response = self.client.get(self.profile_url)
        content = response.content.decode()

        self.assertContains(response, reverse("users:password_change"))
        self.assertContains(response, reverse("users:logout"))
        self.assertContains(response, reverse("users:cv_page"))
        self.assertContains(response, reverse("orders:list"))
        self.assertContains(response, reverse("inbox:thread_list"))
        self.assertIn('method="post"', content)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_existing_account_navigation_targets_are_available(self):
        for name in (
            "users:password_change",
            "users:cv_page",
            "orders:list",
            "inbox:thread_list",
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

        response = self.client.post(reverse("users:logout"))

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_update_persists_fields_and_avatar_and_shows_success(self):
        response = self.client.post(
            self.profile_url,
            {
                "first_name": "Updated",
                "last_name": "Name",
                "email": "UPDATED@example.com",
                "avatar_choice": "ninja",
            },
            follow=True,
        )

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(self.user.avatar_choice, "ninja")
        self.assertContains(response, "Perfil actualizado correctamente.")
        self.assertRegex(
            response.content.decode(),
            r'id="avatar-ninja"[^>]*checked',
        )

    def test_invalid_profile_update_renders_associated_errors_without_saving(self):
        response = self.client.post(
            self.profile_url,
            {
                "first_name": "Should not save",
                "last_name": self.user.last_name,
                "email": "",
                "avatar_choice": "not-a-preset",
            },
        )

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.first_name, "Profile")
        self.assertEqual(self.user.email, "owner@example.com")
        self.assertEqual(self.user.avatar_choice, "")
        self.assertContains(response, 'aria-describedby="profile-email-feedback"')
        self.assertContains(response, 'id="profile-email-feedback"')
        form = response.context["form"]
        self.assertTrue(form.errors["email"])
        self.assertTrue(form.errors["avatar_choice"])
        self.assertContains(response, str(form.errors["email"][0]))
        self.assertContains(response, str(form.errors["avatar_choice"][0]))

    def test_profile_rejects_post_without_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)

        response = client.post(
            self.profile_url,
            {
                "first_name": "Should not save",
                "last_name": self.user.last_name,
                "email": self.user.email,
                "avatar_choice": "dev",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Profile")
