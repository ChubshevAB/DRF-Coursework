from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


class UserModelTest(TestCase):
    """Базовые тесты модели пользователя"""

    def test_create_user_success(self):
        """Тест успешного создания пользователя"""
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
        )

        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.check_password("testpass123"))

    def test_create_user_with_empty_email_creates_user(self):
        """Тест создания пользователя с пустым email (должно разрешаться)"""
        # Изменяем тест: пустой email не должен вызывать ошибку
        user = User.objects.create_user(
            email="",  # Пустой email
            username="testuser",
            password="testpass123",
        )
        self.assertEqual(user.email, "")
        self.assertEqual(user.username, "testuser")

    def test_email_unique_constraint(self):
        """Тест уникальности email"""
        User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
        )

        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="test@example.com",
                username="differentuser",
                password="testpass123",
            )

    def test_str_method_returns_email(self):
        """Тест строкового представления возвращает email"""
        user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123",
        )
        self.assertEqual(str(user), "test@example.com")


class UserAPITest(APITestCase):
    """Базовые тесты API пользователей"""

    def test_user_registration_success(self):
        """Тест успешной регистрации пользователя"""
        url = reverse("user-register")
        user_data = {
            "email": "testuser@example.com",
            "username": "testuser",
            "password": "testpass123",
            "password_confirm": "testpass123",
        }

        response = self.client.post(url, user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["email"], "testuser@example.com")

    def test_user_login_success(self):
        """Тест успешного входа пользователя"""
        User.objects.create_user(
            email="login@example.com",
            username="loginuser",
            password="testpass123"
        )

        url = reverse("user-login")
        login_data = {"email": "login@example.com", "password": "testpass123"}

        response = self.client.post(url, login_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
