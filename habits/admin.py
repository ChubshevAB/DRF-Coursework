from django.contrib import admin
from .models import Habit


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "time", "place", "is_pleasant", "is_public")
    list_filter = ("is_pleasant", "is_public", "frequency")
    search_fields = ("action", "place", "user__username")
