from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

from habits.validators import validate_frequency, HabitCompletionValidator


class Habit(models.Model):

    DAILY = 1
    WEEKLY = 7
    MONTHLY = 30

    PERIOD_CHOICES = [
        (DAILY, "Ежедневно"),
        (WEEKLY, "Еженедельно"),
        (MONTHLY, "Ежемесячно"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="пользователь"
    )
    place = models.CharField(max_length=255, verbose_name="место")
    time = models.TimeField(verbose_name="время")
    action = models.CharField(max_length=255, verbose_name="действие")
    is_pleasant = models.BooleanField(
        default=False, verbose_name="признак приятной привычки"
    )
    related_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="связанная привычка",
    )
    frequency = models.PositiveSmallIntegerField(
        choices=PERIOD_CHOICES,
        default=DAILY,
        verbose_name="периодичность",
        validators=[validate_frequency],
    )
    reward = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="вознаграждение"
    )
    duration = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        verbose_name="время на выполнение (в секундах)",
    )
    is_public = models.BooleanField(default=False, verbose_name="признак публичности")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="дата создания")

    class Meta:
        verbose_name = "привычка"
        verbose_name_plural = "привычки"
        ordering = ["id"]

    def __str__(self):
        return f"{self.user} будет {self.action} в {self.time} в {self.place}"

    def clean(self):
        """
        Валидация на уровне модели:
        - У приятной привычки не может быть вознаграждения или связанной привычки
        - Нельзя указывать одновременно связанную привычку и вознаграждение
        - В связанные привычки можно попасть только привычки с признаком приятной привычки
        - Время выполнения не должно превышать 120 секунд
        """
        from django.core.exceptions import ValidationError

        if self.is_pleasant:
            if self.reward:
                raise ValidationError(
                    "У приятной привычки не может быть вознаграждения."
                )
            if self.related_habit:
                raise ValidationError(
                    "У приятной привычки не может быть связанной привычки."
                )
        else:
            if self.related_habit and self.reward:
                raise ValidationError(
                    "Нельзя указывать одновременно связанную привычку и вознаграждение."
                )
            if self.related_habit and not self.related_habit.is_pleasant:
                raise ValidationError(
                    "В связанные привычки можно добавлять только приятные привычки."
                )

    def save(self, *args, **kwargs):

        self.clean()

        HabitCompletionValidator.validate_habit_before_save(self)

        super().save(*args, **kwargs)


class HabitCompletion(models.Model):
    habit = models.ForeignKey(
        Habit, on_delete=models.CASCADE, related_name="completions"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ["habit", "user", "date"]
