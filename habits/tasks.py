from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Avg
import logging

from .models import Habit, HabitCompletion
from .services import HabitReminderService

logger = logging.getLogger(__name__)


@shared_task
def check_habit_completions():
    """
    Ежедневная проверка выполнения привычек.
    Проверяет, какие привычки не выполнялись более 7 дней и отправляет напоминания.
    """
    try:
        seven_days_ago = timezone.now().date() - timedelta(days=7)
        reminded_habits_count = 0

        for habit in Habit.objects.all():
            last_completion = (
                habit.completions.filter(user=habit.user).order_by("-date").first()
            )

            should_remind = False
            reason = ""

            if last_completion is None:
                if habit.created_at.date() < seven_days_ago:
                    should_remind = True
                    reason = "Привычка никогда не выполнялась"
            else:
                if last_completion.date < seven_days_ago:
                    should_remind = True
                    reason = f"Не выполнялась более 7 дней (последний раз: {last_completion.date})"

            if should_remind:
                try:
                    HabitReminderService.send_reminder_notification(
                        habit.user, habit, message_type="inactive", reason=reason
                    )
                    reminded_habits_count += 1
                    logger.info(
                        f"Напоминание отправлено для привычки {habit.id} пользователя {habit.user.email}: {reason}"
                    )
                except Exception as e:
                    logger.error(
                        f"Ошибка при отправке напоминания для привычки {habit.id}: {e}"
                    )

        logger.info(
            f"Проверка выполнения привычек завершена. Отправлено напоминаний: {reminded_habits_count}"
        )
        return f"Проверка выполнения привычек завершена. Отправлено напоминаний: {reminded_habits_count}"

    except Exception as e:
        logger.error(f"Ошибка в задаче check_habit_completions: {e}")
        return f"Ошибка: {e}"


@shared_task
def send_daily_reminders():
    """
    Ежечасная отправка напоминаний о предстоящих привычках.
    Проверяет привычки, которые должны быть выполнены в ближайший час.
    """
    try:
        now = timezone.localtime()
        current_time = now.time()
        current_date = now.date()
        reminded_habits_count = 0

        time_end = (now + timedelta(hours=1)).time()

        habits_to_remind = Habit.objects.filter(
            time__gte=current_time, time__lte=time_end
        )

        for habit in habits_to_remind:
            today_completion = HabitCompletion.objects.filter(
                habit=habit, user=habit.user, date=current_date
            ).exists()

            if not today_completion:
                try:
                    HabitReminderService.send_reminder_notification(habit.user, habit)
                    reminded_habits_count += 1
                    logger.info(
                        f"Ежедневное напоминание отправлено для привычки {habit.id} пользователя {habit.user.email}"
                    )
                except Exception as e:
                    logger.error(
                        f"Ошибка при отправке ежедневного напоминания для привычки {habit.id}: {e}"
                    )

        logger.info(
            f"Ежедневные напоминания отправлены. Обработано привычек: {reminded_habits_count}"
        )
        return f"Ежедневные напоминания отправлены для {reminded_habits_count} привычек"

    except Exception as e:
        logger.error(f"Ошибка в задаче send_daily_reminders: {e}")
        return f"Ошибка: {e}"


@shared_task
def send_morning_reminders():
    """
    Утренняя рассылка напоминаний о всех привычках на сегодня.
    Запускается каждый день утром.
    """
    try:
        today = timezone.localtime().date()
        reminded_habits_count = 0

        habits = Habit.objects.all()

        for habit in habits:
            today_completion = HabitCompletion.objects.filter(
                habit=habit, user=habit.user, date=today
            ).exists()

            if not today_completion:
                try:
                    HabitReminderService.send_reminder_notification(
                        habit.user, habit, message_type="morning"
                    )
                    reminded_habits_count += 1
                    logger.info(
                        f"Утреннее напоминание отправлено для привычки {habit.id} пользователя {habit.user.email}"
                    )
                except Exception as e:
                    logger.error(
                        f"Ошибка при отправке утреннего напоминания для привычки {habit.id}: {e}"
                    )

        logger.info(
            f"Утренние напоминания отправлены. Обработано привычек: {reminded_habits_count}"
        )
        return f"Утренние напоминания отправлены для {reminded_habits_count} привычек"

    except Exception as e:
        logger.error(f"Ошибка в задаче send_morning_reminders: {e}")
        return f"Ошибка: {e}"


@shared_task
def cleanup_old_completions():
    """
    Очистка старых записей о выполнении привычек.
    Сохраняем только записи за последние 90 дней.
    """
    try:
        ninety_days_ago = timezone.now().date() - timedelta(days=90)
        old_completions = HabitCompletion.objects.filter(date__lt=ninety_days_ago)
        deleted_count = old_completions.count()
        old_completions.delete()

        logger.info(
            f"Очистка старых записей завершена. Удалено записей: {deleted_count}"
        )
        return f"Удалено {deleted_count} старых записей о выполнении"

    except Exception as e:
        logger.error(f"Ошибка в задаче cleanup_old_completions: {e}")
        return f"Ошибка: {e}"


@shared_task
def calculate_habit_statistics():
    """
    Расчет статистики по выполнению привычек.
    Запускается ежедневно.
    """
    try:
        total_completions = HabitCompletion.objects.count()

        stats = {
            "date": timezone.now().date().isoformat(),
            "total_habits": Habit.objects.count(),
            "total_completions": total_completions,
            "active_users": Habit.objects.values("user").distinct().count(),
            "public_habits": Habit.objects.filter(is_public=True).count(),
            "pleasant_habits": Habit.objects.filter(is_pleasant=True).count(),
            "useful_habits": Habit.objects.filter(is_pleasant=False).count(),
            "avg_completions_per_user": HabitCompletion.objects.values("user")
            .annotate(count=Count("id"))
            .aggregate(avg=Avg("count"))["avg"]
            or 0,
            "most_popular_habit": HabitCompletion.objects.values(
                "habit__action", "habit__user__email"
            )
            .annotate(count=Count("id"))
            .order_by("-count")
            .first(),
            "most_consistent_user": HabitCompletion.objects.values("user__email")
            .annotate(count=Count("id"))
            .order_by("-count")
            .first(),
            "completions_last_7_days": HabitCompletion.objects.filter(
                date__gte=timezone.now().date() - timedelta(days=7)
            ).count(),
            "completions_last_30_days": HabitCompletion.objects.filter(
                date__gte=timezone.now().date() - timedelta(days=30)
            ).count(),
        }

        logger.info(f"Статистика привычек рассчитана: {stats}")

        return stats

    except Exception as e:
        logger.error(f"Ошибка в задаче calculate_habit_statistics: {e}")
        return {"error": str(e)}


@shared_task
def test_telegram_notification(user_id=None, message="Тестовое уведомление"):
    """
    Тестовая задача для проверки работы Telegram уведомлений.
    """
    try:
        from users.models import User

        if user_id:
            user = User.objects.get(id=user_id)
            habit = Habit.objects.filter(user=user).first()

            if habit and user.telegram_chat_id:
                HabitReminderService.send_reminder_notification(
                    user, habit, message_type="test", custom_message=message
                )
                return f"Тестовое уведомление отправлено пользователю {user.email}"
            else:
                return "Пользователь не найден или не имеет привычек/Telegram Chat ID"
        else:
            admin_users = User.objects.filter(is_staff=True)
            for admin in admin_users:
                if admin.telegram_chat_id:
                    HabitReminderService.send_reminder_notification(
                        admin, None, message_type="test", custom_message=message
                    )
            return "Тестовое уведомление отправлено администраторам"

    except Exception as e:
        logger.error(f"Ошибка в тестовой задаче: {e}")
        return f"Ошибка: {e}"
