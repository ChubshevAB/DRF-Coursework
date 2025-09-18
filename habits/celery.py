import os
from celery import Celery
from celery.schedules import crontab


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "send-daily-reminders-every-hour": {
        "task": "habits.tasks.send_daily_reminders",
        "schedule": crontab(minute=0, hour="*/1"),
    },
    "check-completions-every-day": {
        "task": "habits.tasks.check_habit_completions",
        "schedule": crontab(minute=0, hour=9),
    },
    "send-morning-reminders": {
        "task": "habits.tasks.send_morning_reminders",
        "schedule": crontab(minute=30, hour=7),
    },
    "cleanup-old-completions-every-week": {
        "task": "habits.tasks.cleanup_old_completions",
        "schedule": crontab(minute=0, hour=3, day_of_week=1),
    },
    "calculate-habit-statistics-daily": {
        "task": "habits.tasks.calculate_habit_statistics",
        "schedule": crontab(minute=0, hour=23),
    },
}

app.conf.timezone = "UTC"
app.conf.enable_utc = True
