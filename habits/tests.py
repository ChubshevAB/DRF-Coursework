from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.utils import timezone
from datetime import time, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from habits.models import Habit, HabitCompletion
from habits.validators import validate_frequency, HabitCompletionValidator
from habits.services import HabitTrackerService, HabitReminderService, TelegramService

User = get_user_model()


class HabitModelTest(TestCase):
    """Тесты для модели привычки"""

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
            frequency=Habit.DAILY,
        )

        self.assertEqual(habit.user, self.user)
        self.assertEqual(habit.place, "Дом")
        self.assertEqual(habit.action, "Читать книгу")
        self.assertEqual(habit.duration, 60)
        self.assertEqual(habit.frequency, Habit.DAILY)
        self.assertFalse(habit.is_pleasant)
        self.assertFalse(habit.is_public)
        self.assertIsNone(habit.related_habit)
        self.assertIsNone(habit.reward)

    def test_pleasant_habit_with_reward_raises_validation_error(self):
        """Тест приятной привычки с вознаграждением вызывает ValidationError"""
        habit = Habit(
            user=self.user,
            place="Парк",
            time=time(10, 0),
            action="Гулять",
            duration=30,
            is_pleasant=True,
            reward="Шоколадка",  # Не должно быть у приятной привычки
        )

        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_pleasant_habit_with_related_habit_raises_validation_error(self):
        """Тест приятной привычки со связанной привычкой вызывает ValidationError"""
        pleasant_habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(8, 0),
            action="Медитировать",
            duration=15,
            is_pleasant=True,
        )

        habit = Habit(
            user=self.user,
            place="Парк",
            time=time(10, 0),
            action="Гулять",
            duration=30,
            is_pleasant=True,
            related_habit=pleasant_habit,  # Не должно быть у приятной привычки
        )

        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_useful_habit_with_both_reward_and_related_habit_raises_validation_error(self):
        """Тест полезной привычки с вознаграждением и связанной привычкой вызывает ValidationError"""
        pleasant_habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(8, 0),
            action="Медитировать",
            duration=15,
            is_pleasant=True,
        )

        useful_habit = Habit(
            user=self.user,
            place="Спортзал",
            time=time(19, 0),
            action="Тренироваться",
            duration=45,
            related_habit=pleasant_habit,
            reward="Отдых",  # Должно быть ИЛИ связанная привычка ИЛИ вознаграждение
        )

        with self.assertRaises(ValidationError):
            useful_habit.full_clean()

    def test_habit_with_excessive_duration_raises_validation_error(self):
        """Тест привычки с длительностью более 120 секунд вызывает ValidationError"""
        habit = Habit(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Тест",
            duration=121,  # Превышает лимит в 120 секунд
        )

        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_habit_with_zero_duration_raises_validation_error(self):
        """Тест привычки с нулевой длительностью вызывает ValidationError"""
        habit = Habit(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Тест",
            duration=0,  # Не может быть нулевой
        )

        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_habit_with_negative_duration_raises_validation_error(self):
        """Тест привычки с отрицательной длительностью вызывает ValidationError"""
        habit = Habit(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Тест",
            duration=-10,  # Не может быть отрицательной
        )

        with self.assertRaises(ValidationError):
            habit.full_clean()

    def test_habit_string_representation(self):
        """Тест строкового представления привычки"""
        habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Читать книгу",
            duration=30,
        )

        expected_str = f"Читать книгу в Дом в 09:00:00"
        self.assertEqual(str(habit), expected_str)


class HabitValidatorTest(TestCase):
    """Тесты валидаторов привычек"""

    def test_validate_frequency_with_valid_value_success(self):
        """Тест валидации корректной периодичности"""
        # Должно пройти без исключений
        validate_frequency(7)  # MAX_FREQUENCY
        validate_frequency(1)  # MIN_FREQUENCY
        validate_frequency(3)  # Среднее значение

    def test_validate_frequency_with_invalid_value_raises_validation_error(self):
        """Тест валидации некорректной периодичности вызывает ValidationError"""
        with self.assertRaises(ValidationError):
            validate_frequency(0)  # Меньше минимального

        with self.assertRaises(ValidationError):
            validate_frequency(8)  # Больше максимального

        with self.assertRaises(ValidationError):
            validate_frequency(-1)  # Отрицательное значение

    def test_habit_completion_validator_duplicate_date_raises_error(self):
        """Тест валидатора выполнения привычки на дубликат даты"""
        user = User.objects.create_user(
            email="validator@example.com",
            username="validatoruser",
            password="testpass123",
        )

        habit = Habit.objects.create(
            user=user,
            place="Дом",
            time=time(9, 0),
            action="Тест",
            duration=30
        )

        old_date = timezone.now().date() - timedelta(days=1)
        HabitCompletion.objects.create(habit=habit, user=user, date=old_date)

        with self.assertRaises(ValidationError):
            HabitCompletionValidator.validate_habit_completion(habit, old_date)

    def test_habit_completion_validator_future_date_raises_error(self):
        """Тест валидатора выполнения привычки на будущую дату"""
        user = User.objects.create_user(
            email="validator@example.com",
            username="validatoruser",
            password="testpass123",
        )

        habit = Habit.objects.create(
            user=user,
            place="Дом",
            time=time(9, 0),
            action="Тест",
            duration=30
        )

        future_date = timezone.now().date() + timedelta(days=1)

        with self.assertRaises(ValidationError):
            HabitCompletionValidator.validate_habit_completion(habit, future_date)


class HabitAPITest(APITestCase):
    """Тесты API привычек"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="api@example.com",
            username="apiuser",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            username="otheruser",
            password="testpass123"
        )

        self.habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Читать",
            duration=30,
            frequency=Habit.DAILY,
        )

        self.public_habit = Habit.objects.create(
            user=self.other_user,
            place="Парк",
            time=time(10, 0),
            action="Гулять",
            duration=45,
            is_public=True,
        )

        self.pleasant_habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(20, 0),
            action="Слушать музыку",
            duration=20,
            is_pleasant=True,
        )

    def test_create_habit_authenticated_success(self):
        """Тест успешного создания привычки через API с аутентификацией"""
        self.client.force_authenticate(user=self.user)

        url = reverse("habit-list")
        habit_data = {
            "place": "Офис",
            "time": "15:00:00",
            "action": "Работать",
            "duration": 120,
            "frequency": Habit.DAILY,
        }

        response = self.client.post(url, habit_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["action"], "Работать")
        self.assertEqual(response.data["duration"], 120)
        self.assertEqual(response.data["frequency"], Habit.DAILY)

    def test_create_habit_unauthenticated_returns_error(self):
        """Тест создания привычки без аутентификации возвращает ошибку"""
        url = reverse("habit-list")
        habit_data = {
            "place": "Офис",
            "time": "15:00:00",
            "action": "Работать",
            "duration": 60,
        }

        response = self.client.post(url, habit_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_habit_with_invalid_duration_returns_error(self):
        """Тест создания привычки с некорректной длительностью возвращает ошибку"""
        self.client.force_authenticate(user=self.user)

        url = reverse("habit-list")
        habit_data = {
            "place": "Офис",
            "time": "15:00:00",
            "action": "Работать",
            "duration": 121,  # Превышает лимит
        }

        response = self.client.post(url, habit_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_my_habits_authenticated_success(self):
        """Тест успешного получения списка своих привычек"""
        self.client.force_authenticate(user=self.user)

        url = reverse("habit-my-habits")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # 2 привычки у пользователя

    def test_list_my_habits_unauthenticated_returns_error(self):
        """Тест получения списка своих привычек без аутентификации возвращает ошибку"""
        url = reverse("habit-my-habits")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_public_habits_success(self):
        """Тест успешного получения списка публичных привычек"""
        self.client.force_authenticate(user=self.user)

        url = reverse("habit-public-habits")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["action"], "Гулять")

    def test_update_own_habit_success(self):
        """Тест успешного обновления своей привычки"""
        self.client.force_authenticate(user=self.user)

        url = reverse("habit-detail", kwargs={"pk": self.habit.pk})
        update_data = {"action": "Читать больше"}

        response = self.client.patch(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["action"], "Читать больше")

    def test_update_other_user_habit_returns_not_found(self):
        """Тест попытки обновления чужой привычки возвращает 404"""
        self.client.force_authenticate(user=self.other_user)

        url = reverse("habit-detail", kwargs={"pk": self.habit.pk})
        update_data = {"action": "Взломать привычку"}

        response = self.client.patch(url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_habit_completed_success(self):
        """Тест успешной отметки выполнения привычки"""
        self.client.force_authenticate(user=self.user)

        url = reverse("habit-mark-completed", kwargs={"pk": self.habit.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(HabitCompletion.objects.filter(habit=self.habit).exists())

    def test_mark_habit_completed_twice_returns_error(self):
        """Тест повторной отметки выполнения привычки возвращает ошибку"""
        self.client.force_authenticate(user=self.user)

        url = reverse("habit-mark-completed", kwargs={"pk": self.habit.pk})
        self.client.post(url)  # Первый раз

        response = self.client.post(url)  # Второй раз
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_toggle_public_success(self):
        """Тест успешного переключения публичности привычки"""
        self.client.force_authenticate(user=self.user)

        url = reverse("habit-toggle-public", kwargs={"pk": self.habit.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.habit.refresh_from_db()
        self.assertTrue(self.habit.is_public)

    def test_get_habit_completions_success(self):
        """Тест успешного получения истории выполнений"""
        self.client.force_authenticate(user=self.user)

        # Создаем выполнения
        HabitCompletion.objects.create(habit=self.habit, user=self.user)
        HabitCompletion.objects.create(
            habit=self.habit,
            user=self.user,
            date=timezone.now().date() - timedelta(days=1),
        )

        url = reverse("habit-completions")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Одна привычка с выполнениями
        self.assertEqual(len(response.data[0]["completions"]), 2)  # Два выполнения


class HabitServiceTest(TestCase):
    """Тесты сервисного слоя"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="service@example.com",
            username="serviceuser",
            password="testpass123"
        )

        self.habit = Habit.objects.create(
            user=self.user,
            place="Дом",
            time=time(9, 0),
            action="Тест сервиса",
            duration=30,
        )

    def test_mark_habit_completed_service_success(self):
        """Тест успешной отметки выполнения через сервис"""
        result = HabitTrackerService.mark_habit_completed(self.habit, self.user)
        self.assertTrue(result)
        self.assertEqual(self.habit.completions.count(), 1)

    def test_mark_habit_completed_service_duplicate_raises_error(self):
        """Тест повторной отметки выполнения через сервис вызывает ошибку"""
        HabitTrackerService.mark_habit_completed(self.habit, self.user)

        with self.assertRaises(ValidationError):
            HabitTrackerService.mark_habit_completed(self.habit, self.user)

    def test_habit_reminder_service_success(self):
        """Тест сервиса напоминаний возвращает True"""
        result = HabitReminderService.send_reminder_notification(self.user, self.habit)
        self.assertTrue(result)

    def test_habit_reminder_service_without_telegram_chat_id(self):
        """Тест сервиса напоминаний без telegram_chat_id"""
        user_without_telegram = User.objects.create_user(
            email="notelegram@example.com",
            username="notelegramuser",
            password="testpass123"
        )

        result = HabitReminderService.send_reminder_notification(user_without_telegram, self.habit)
        self.assertFalse(result)  # Должно вернуть False, так как нет telegram_chat_id


class HabitPaginationTest(APITestCase):
    """Тесты пагинации привычек"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="pagination@example.com",
            username="paginationuser",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        # Создаем 10 привычек
        for i in range(10):
            Habit.objects.create(
                user=self.user,
                place=f"Место {i}",
                time=time(9 + i, 0),
                action=f"Действие {i}",
                duration=30,
            )

    def test_pagination_returns_five_habits_per_page(self):
        """Тест пагинации по 5 привычек на страницу"""
        url = reverse("habit-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_pagination_second_page_returns_five_habits(self):
        """Тест второй страницы пагинации возвращает 5 привычек"""
        url = reverse("habit-list") + "?page=2"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)


class TelegramServiceTest(TestCase):
    """Тесты Telegram сервиса"""

    def test_telegram_service_initialization_success(self):
        """Тест успешной инициализации Telegram сервиса"""
        service = TelegramService()
        self.assertIsInstance(service, TelegramService)

    def test_telegram_service_has_required_methods(self):
        """Тест наличия обязательных методов в Telegram сервисе"""
        service = TelegramService()

        # Проверяем наличие основных методов
        self.assertTrue(hasattr(service, 'send_message'))
        self.assertTrue(hasattr(service, 'bot'))
        self.assertTrue(hasattr(service, 'send_reminder'))

    def test_telegram_service_send_message_returns_bool(self):
        """Тест что метод send_message возвращает boolean"""
        service = TelegramService()

        result = service.send_message("123456789", "Test message")
        self.assertIsInstance(result, bool)
