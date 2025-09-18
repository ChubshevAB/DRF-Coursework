from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

User = get_user_model()


class UserModelTest(TestCase):
    """Тесты для модели пользователя"""

    def setUp(self):
        self.user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpass123",
        }

    def test_create_user_success(self):
        """Тест успешного создания пользователя"""
        user = User.objects.create_user(**self.user_data)

        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)

    def test_create_user_without_email_raises_error(self):
        """Тест создания пользователя без email вызывает ошибку"""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="", username="testuser", password="testpass123"
            )

    def test_create_superuser_success(self):
        """Тест успешного создания суперпользователя"""
        admin_user = User.objects.create_superuser(
            email="admin@example.com", username="admin", password="adminpass123"
        )

        self.assertEqual(admin_user.email, "admin@example.com")
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_create_superuser_without_staff_status_raises_error(self):
        """Тест создания суперпользователя без is_staff вызывает ошибку"""
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com",
                username="admin",
                password="adminpass123",
                is_staff=False,
            )

    def test_create_superuser_without_superuser_status_raises_error(self):
        """Тест создания суперпользователя без is_superuser вызывает ошибку"""
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com",
                username="admin",
                password="adminpass123",
                is_superuser=False,
            )

    def test_email_unique_constraint(self):
        """Тест ограничения уникальности email"""
        User.objects.create_user(**self.user_data)

        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="test@example.com",
                username="differentuser",
                password="testpass123",
            )

    def test_str_method_returns_email(self):
        """Тест строкового представления возвращает email"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), "test@example.com")

    def test_user_creation_with_extra_fields(self):
        """Тест создания пользователя с дополнительными полями"""
        user = User.objects.create_user(
            email="extra@example.com",
            username="extrauser",
            password="testpass123",
            first_name="Test",
            last_name="User",
            telegram_chat_id="123456789",
        )

        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.telegram_chat_id, "123456789")


class UserAPITest(APITestCase):
    """Тесты API пользователей"""

    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            "email": "testuser@example.com",
            "username": "testuser",
            "password": "testpass123",
            "password_confirm": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        }
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com", username="admin", password="adminpass123"
        )

    def test_user_registration_success(self):
        """Тест успешной регистрации пользователя"""
        url = reverse("user-register")
        response = self.client.post(url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "testuser@example.com")
        self.assertEqual(response.data["user"]["username"], "testuser")

    def test_user_registration_with_password_mismatch_returns_error(self):
        """Тест регистрации с несовпадающими паролями возвращает ошибку"""
        data = self.user_data.copy()
        data["password_confirm"] = "differentpassword"
        url = reverse("user-register")

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_user_registration_with_invalid_email_returns_error(self):
        """Тест регистрации с некорректным email возвращает ошибку"""
        data = self.user_data.copy()
        data["email"] = "invalid-email"
        url = reverse("user-register")

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_user_login_success(self):
        """Тест успешного входа пользователя"""
        User.objects.create_user(
            email="login@example.com", username="loginuser", password="testpass123"
        )

        url = reverse("user-login")
        login_data = {"email": "login@example.com", "password": "testpass123"}

        response = self.client.post(url, login_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_user_login_with_invalid_credentials_returns_error(self):
        """Тест входа с неверными учетными данными возвращает ошибку"""
        url = reverse("user-login")
        login_data = {"email": "nonexistent@example.com", "password": "wrongpassword"}

        response = self.client.post(url, login_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_current_user_info_authenticated(self):
        """Тест получения информации о текущем пользователе с аутентификацией"""
        user = User.objects.create_user(
            email="current@example.com", username="currentuser", password="testpass123"
        )
        self.client.force_authenticate(user=user)

        url = reverse("user-me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "current@example.com")
        self.assertEqual(response.data["username"], "currentuser")

    def test_get_current_user_info_unauthenticated_returns_error(self):
        """Тест получения информации о текущем пользователе без аутентификации возвращает ошибку"""
        url = reverse("user-me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_profile_success(self):
        """Тест успешного обновления профиля пользователя"""
        user = User.objects.create_user(
            email="update@example.com", username="updateuser", password="testpass123"
        )
        self.client.force_authenticate(user=user)

        url = reverse("user-detail", kwargs={"pk": user.pk})
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "telegram_chat_id": "123456789",
        }

        response = self.client.patch(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["last_name"], "Name")
        self.assertEqual(response.data["telegram_chat_id"], "123456789")

    def test_list_users_as_admin_success(self):
        """Тест получения списка пользователей администратором"""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("user-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_users_as_regular_user_returns_forbidden(self):
        """Тест получения списка пользователей обычным пользователем возвращает запрет"""
        user = User.objects.create_user(
            email="regular@example.com", username="regularuser", password="testpass123"
        )
        self.client.force_authenticate(user=user)

        url = reverse("user-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_users_unauthenticated_returns_error(self):
        """Тест получения списка пользователей без аутентификации возвращает ошибку"""
        url = reverse("user-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
