"""Seed django_celery_beat schedules for the photo-cleanup tasks.

The cleanup tasks in ``footycollect.collection.tasks`` are only useful with a
running celerybeat, and beat uses the DatabaseScheduler — so the periodic
entries must exist in the DB. Nothing else registers them, so this data
migration seeds sensible defaults (idempotent, reversible). Adjust or disable
them later in Django admin (Periodic Tasks) as you like.
"""

from __future__ import annotations

from django.db import migrations

# name -> (dotted task path, crontab fields). Cron in the app timezone.
CLEANUP_SCHEDULES = [
    (
        "cleanup orphaned photos (incomplete >24h)",
        "footycollect.collection.tasks.cleanup_orphaned_photos",
        {"minute": "30", "hour": "3", "day_of_week": "*", "day_of_month": "*", "month_of_year": "*"},
    ),
    (
        "cleanup old incomplete photos (incomplete >168h)",
        "footycollect.collection.tasks.cleanup_old_incomplete_photos",
        {"minute": "45", "hour": "3", "day_of_week": "1", "day_of_month": "*", "month_of_year": "*"},
    ),
    (
        "cleanup all orphaned photos (comprehensive)",
        "footycollect.collection.tasks.cleanup_all_orphaned_photos",
        {"minute": "0", "hour": "4", "day_of_week": "0", "day_of_month": "*", "month_of_year": "*"},
    ),
]


def seed_schedules(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    for name, task, cron in CLEANUP_SCHEDULES:
        crontab, _ = CrontabSchedule.objects.get_or_create(**cron)
        PeriodicTask.objects.update_or_create(
            name=name,
            defaults={"task": task, "crontab": crontab, "enabled": True},
        )


def unseed_schedules(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name__in=[name for name, _, _ in CLEANUP_SCHEDULES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("collection", "0005_add_jersey_fit_private"),
        ("django_celery_beat", "__latest__"),
    ]

    operations = [migrations.RunPython(seed_schedules, unseed_schedules)]
