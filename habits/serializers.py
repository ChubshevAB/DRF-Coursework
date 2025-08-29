from rest_framework import serializers
from .models import Habit
from .validators import HabitCompletionValidator


class HabitSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Habit
        fields = "__all__"
        read_only_fields = ("user",)

    def validate(self, data):
        """
        Валидация данных на уровне сериализатора
        """
        is_pleasant = data.get(
            "is_pleasant", self.instance.is_pleasant if self.instance else False
        )
        related_habit = data.get("related_habit")
        reward = data.get("reward")

        if is_pleasant:
            if reward:
                raise serializers.ValidationError(
                    "У приятной привычки не может быть вознаграждения."
                )
            if related_habit:
                raise serializers.ValidationError(
                    "У приятной привычки не может быть связанной привычки."
                )
        else:

            if related_habit and reward:
                raise serializers.ValidationError(
                    "Нельзя указывать одновременно связанную привычку и вознаграждение."
                )

            if related_habit and not related_habit.is_pleasant:
                raise serializers.ValidationError(
                    "В связанные привычки можно добавлять только приятные привычки."
                )

        duration = data.get("duration")
        if duration and duration > 120:
            raise serializers.ValidationError(
                "Время выполнения не может превышать 120 минут."
            )

        if not self.instance:
            HabitCompletionValidator.validate_habit_frequency_on_creation(data)

        return data

    def create(self, validated_data):
        """
        Создание привычки с дополнительной валидацией
        """

        HabitCompletionValidator.validate_habit_frequency_on_creation(validated_data)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Обновление привычки с дополнительной валидацией
        """

        HabitCompletionValidator.validate_habit_consistency(instance)

        return super().update(instance, validated_data)
