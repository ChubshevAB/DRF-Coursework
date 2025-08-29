from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


def validate_frequency(value):
    """
    Валидатор для проверки, что привычка выполняется не реже 1 раза в 7 дней
    """
    if value > 7:
        raise ValidationError("Нельзя выполнять привычку реже, чем 1 раз в 7 дней.")


class HabitCompletionValidator:
    """
    Валидатор для проверки выполнения привычки не реже 1 раза в 7 дней
    """

    @staticmethod
    def validate_habit_completion(habit, last_completion_date):
        """
        Проверяет, что привычка выполняется не реже 1 раза в 7 дней
        """
        if last_completion_date:
            days_since_last_completion = (
                timezone.now().date() - last_completion_date
            ).days
            if days_since_last_completion > 7:
                raise ValidationError(
                    f"Привычка не выполнялась более 7 дней. "
                    f"Последнее выполнение: {last_completion_date}"
                )

    @staticmethod
    def validate_habit_frequency_on_creation(habit_data):
        """
        Проверяет периодичность привычки при создании
        Нельзя создавать привычку с периодичностью более 7 дней
        """
        frequency = habit_data.get("frequency")

        if frequency and frequency > 7:
            raise ValidationError(
                "Нельзя создавать привычку с периодичностью более 7 дней. "
                "Привычка должна выполняться не реже 1 раза в 7 дней."
            )

    @staticmethod
    def validate_habit_consistency(habit_instance):
        """
        Проверяет, что привычка не нарушает правило "не более 7 дней без выполнения"
        при создании или обновлении
        """

        if not habit_instance.pk:
            return

        seven_days_ago = timezone.now().date() - timedelta(days=7)
        recent_completion = habit_instance.completions.filter(
            date__gte=seven_days_ago
        ).exists()

        if not recent_completion:
            creation_date = habit_instance.created_at.date()
            if creation_date < seven_days_ago:
                raise ValidationError(
                    "Привычка не выполнялась более 7 дней. "
                    "Нельзя обновлять привычку, которая не выполняется регулярно."
                )

    @staticmethod
    def validate_habit_before_save(habit_instance):
        """
        Комплексная валидация привычки перед сохранением
        """

        if habit_instance.frequency > 7:
            raise ValidationError("Нельзя выполнять привычку реже, чем 1 раз в 7 дней.")

        HabitCompletionValidator.validate_habit_consistency(habit_instance)
