import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djbackend.settings")
app = Celery("djbackend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'clean_expired_video': {
        'task': 'main.tasks.clean_expired_records',
        'schedule': crontab(minute='*/2'),
    },
    'clean_lost_video': {
        'task': 'main.tasks.clean_video',
        'schedule': crontab(minute='*/2'),
    },
    'clean_denied_users': {
        'task': 'registration.tasks.clean_denied',
        'schedule': crontab(minute='*/2'),
    },
    'check_nonactive_users': {
        'task': 'registration.tasks.check_nonactive',
        'schedule': crontab(minute='*/2'),
    }
}
