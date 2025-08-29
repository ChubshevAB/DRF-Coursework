import logging
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .validators import HabitCompletionValidator


logger = logging.getLogger(__name__)


class TelegramService:
    """
    Сервис для отправки уведомлений через Telegram
    """

    BASE_URL = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"

    @staticmethod
    def send_message(chat_id, text):
        """
        Отправляет сообщение в Telegram чат
        :param chat_id: ID чата пользователя
        :param text: Текст сообщения
        :return: Ответ от Telegram API
        """
        url = f"{TelegramService.BASE_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при отправке сообщения в Telegram: {e}")
            return None


class HabitTrackerService:
    """
    Сервис для отслеживания выполнения привычек
    """

    @staticmethod
    def mark_habit_completed(habit, user):
        """
        Отмечает выполнение привычки и проверяет периодичность
        """

        today = timezone.now().date()
        if habit.completions.filter(user=user, date=today).exists():
            raise ValidationError("Эта привычка уже отмечена как выполненная сегодня.")

        last_completion = habit.completions.filter(user=user).order_by("-date").first()
        if last_completion:
            HabitCompletionValidator.validate_habit_completion(
                habit, last_completion.date
            )

        habit.completions.create(user=user, date=today)

        return True


class HabitReminderService:
    """
    Сервис для отправки напоминаний о привычках
    """

    @staticmethod
    def send_reminder_notification(
        user, habit, message_type="daily", reason=None, custom_message=None
    ):
        """
        Отправляет уведомление пользователю о необходимости выполнить привычку
        """
        if custom_message:
            message = custom_message
        else:
            if message_type == "inactive":
                message = (
                    f"⚠️ <b>Вы давно не выполняли привычку!</b>\n\n"
                    f"Привычка: <b>{habit.action}</b>\n"
                    f"Причина: {reason}\n"
                    f"Время: <b>{habit.time.strftime('%H:%M')}</b>\n"
                    f"Место: <b>{habit.place}</b>\n"
                    f"Не забудьте возобновить практику! 💪"
                )
            elif message_type == "morning":
                message = (
                    f"🌅 <b>Доброе утро!</b>\n\n"
                    f"Сегодня вас ждет привычка: <b>{habit.action}</b>\n"
                    f"Время: <b>{habit.time.strftime('%H:%M')}</b>\n"
                    f"Место: <b>{habit.place}</b>\n"
                    f"Хорошего дня! ✨"
                )
            else:  # daily
                message = (
                    f"⏰ <b>Напоминание о привычке</b>\n\n"
                    f"Привычка: <b>{habit.action}</b>\n"
                    f"Время: <b>{habit.time.strftime('%H:%M')}</b>\n"
                    f"Место: <b>{habit.place}</b>\n"
                    f"Длительность: <b>{habit.duration} секунд</b>"
                )

        if user.telegram_chat_id:
            result = TelegramService.send_message(user.telegram_chat_id, message)
            if result:
                logger.info(
                    f"Telegram-уведомление отправлено пользователю {user.email} (Chat ID: {user.telegram_chat_id})"
                )
            else:
                logger.error(
                    f"Не удалось отправить Telegram-уведомление пользователю {user.email}"
                )
        else:
            logger.warning(f"Уведомление для {user.email}: {message}")
            logger.warning("⚠️ Telegram Chat ID не указан. Уведомление не отправлено.")

        return True
