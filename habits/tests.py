from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from datetime import time
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from habits.models import Habit
from habits.validators import validate_frequency

User = get_user_model()


class HabitModelTest(TestCase):
    """Базовые тесты модели привычки"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="testpass123"
        )

    def test_create_habit_success(self):
        """Тест успешного создания привычки"""
        habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Читать книгу",
            duration=60,
        )

        self.assertEqual(habit.user, self.user)
        self.assertEqual(habit.place, "Дом")
        self.assertEqual(habit.action, "Читать книгу")
        self.assertEqual(habit.duration, 60)
        self.assertFalse(habit.is_pleasant)

    def test_habit_string_representation(self):
        """Тест строкового представления привычки"""
        habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Читать книгу",
            duration=30,
        )

        self.assertIn("Читать книгу", str(habit))
        self.assertIn("Дом", str(habit))


class HabitValidatorTest(TestCase):
    """Тесты валидаторов"""

    def test_validate_frequency_with_valid_value_success(self):
        """Тест валидации корректной периодичности"""
        validate_frequency(7)
        validate_frequency(1)
        validate_frequency(3)

    def test_validate_frequency_with_invalid_value_raises_validation_error(self):
        """Тест валидации некорректной периодичности"""
        with self.assertRaises(ValidationError):
            validate_frequency(0)

        with self.assertRaises(ValidationError):
            validate_frequency(8)


class HabitAPITest(APITestCase):
    """Базовые тесты API"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="api@example.com",
            username="apiuser",
            password="testpass123"
        )

    def test_create_habit_authenticated_success(self):
        """Тест успешного создания привычки через API"""
        self.client.force_authenticate(user=self.user)

        url = reverse("habit-list")
        habit_data = {
            "place": "Офис",
            "time": "15:00:00",
            "action": "Работать",
            "duration": 60,
        }

        response = self.client.post(url, habit_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["action"], "Работать")

    def test_create_habit_unauthenticated_returns_error(self):
        """Тест создания привычки без аутентификации"""
        url = reverse("habit-list")
        habit_data = {
            "place": "Офис",
            "time": "15:00:00",
            "action": "Работать",
            "duration": 60,
        }

        response = self.client.post(url, habit_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_my_habits_authenticated_success(self):
        """Тест получения списка своих привычек"""
        # Создаем привычку
        Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Читать",
            duration=30,
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("habit-my-habits")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
