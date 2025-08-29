from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import Habit
from .serializers import HabitSerializer
from .permissions import IsOwnerOrPublicReadOnly
from .services import HabitTrackerService


class HabitViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с привычками.
    Позволяет:
    - Просматривать свои и публичные привычки других пользователей
    - Создавать, обновлять и удалять только свои привычки
    - Использовать дополнительные эндпоинты для фильтрации
    - Отмечать выполнение привычек
    """

    serializer_class = HabitSerializer
    permission_classes = [IsOwnerOrPublicReadOnly]

    def get_queryset(self):
        """
        Пользователь видит только свои привычки и публичные привычки других пользователей
        """
        user = self.request.user
        return Habit.objects.filter(Q(user=user) | Q(is_public=True))

    def perform_create(self, serializer):
        """
        Автоматически привязываем привычку к текущему пользователю
        """
        serializer.save(user=self.request.user)

    def get_serializer_context(self):
        """
        Передаем контекст с пользователем для валидации
        """
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context

    @action(detail=False, methods=["get"])
    def my_habits(self, request):
        """
        Эндпоинт для получения только своих привычек
        URL: /api/habits/my_habits/
        """
        habits = Habit.objects.filter(user=request.user)
        page = self.paginate_queryset(habits)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(habits, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def public_habits(self, request):
        """
        Эндпоинт для получения публичных привычек других пользователей
        URL: /api/habits/public_habits/
        """
        habits = Habit.objects.filter(is_public=True).exclude(user=request.user)
        page = self.paginate_queryset(habits)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(habits, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pleasant_habits(self, request):
        """
        Эндпоинт для получения приятных привычек
        URL: /api/habits/pleasant_habits/
        """
        habits = Habit.objects.filter(is_pleasant=True)
        if not request.user.is_staff:
            habits = habits.filter(Q(user=request.user) | Q(is_public=True))

        page = self.paginate_queryset(habits)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(habits, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def useful_habits(self, request):
        """
        Эндпоинт для получения полезных привычек (не приятных)
        URL: /api/habits/useful_habits/
        """
        habits = Habit.objects.filter(is_pleasant=False)
        if not request.user.is_staff:
            habits = habits.filter(Q(user=request.user) | Q(is_public=True))

        page = self.paginate_queryset(habits)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(habits, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def toggle_public(self, request, pk=None):
        """
        Эндпоинт для переключения публичности привычки
        URL: /api/habits/{id}/toggle_public/
        """
        habit = self.get_object()

        if habit.user != request.user:
            return Response(
                {"detail": "Вы можете изменять только свои привычки."},
                status=status.HTTP_403_FORBIDDEN,
            )

        habit.is_public = not habit.is_public
        habit.save()

        serializer = self.get_serializer(habit)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_completed(self, request, pk=None):
        """
        Отметить выполнение привычки
        URL: /api/habits/{id}/mark_completed/
        """
        habit = self.get_object()

        if habit.user != request.user:
            return Response(
                {"detail": "Вы можете отмечать выполнение только своих привычек."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            HabitTrackerService.mark_habit_completed(habit, request.user)
            return Response(
                {"detail": "Привычка успешно отмечена как выполненная."},
                status=status.HTTP_200_OK,
            )
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def completions(self, request):
        """
        Эндпоинт для получения истории выполнения привычек
        URL: /api/habits/completions/
        """

        habits = Habit.objects.filter(user=request.user)

        completion_data = []
        for habit in habits:
            completions = habit.completions.filter(user=request.user).order_by("-date")[
                :10
            ]
            completion_data.append(
                {
                    "habit_id": habit.id,
                    "habit_action": habit.action,
                    "completions": [{"date": comp.date} for comp in completions],
                    "last_completion": completions[0].date if completions else None,
                }
            )

        return Response(completion_data)

    def list(self, request, *args, **kwargs):
        """
        Переопределяем метод list для добавления пагинации
        """
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Переопределяем метод retrieve для проверки доступа к конкретной привычке
        """
        instance = self.get_object()

        if not instance.is_public and instance.user != request.user:
            return Response(
                {"detail": "У вас нет доступа к этой привычке."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)
