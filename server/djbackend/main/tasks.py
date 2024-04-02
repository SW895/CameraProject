from djbackend.celery import app
from django.core.cache import cache
from django.conf import settings
from .models import CachedVideo
import datetime
import os
import pytz 


@app.task
def clean_expired_records():
    timezone = pytz.timezone('Europe/Moscow')
    records = CachedVideo.objects.filter(date_expire__lt=datetime.datetime.now(tz=timezone))
    for record in records:
        if os.path.exists(str(settings.MEDIA_ROOT) + '/' + record.name + '.mp4'):
            os.remove(str(settings.MEDIA_ROOT) + '/' + record.name + '.mp4')

    records.delete()


@app.task
def clean_video():
    records = CachedVideo.objects.all()
    actual_names = set()
    for record in records:
        actual_names.add(record.name + '.mp4')

    for file in os.scandir(str(settings.MEDIA_ROOT)):
        if not (file.name in actual_names):
            os.remove(str(settings.MEDIA_ROOT) + '/' + file.name)


@app.task
def update_cache(video_name, timeout=60):
    timezone = pytz.timezone('Europe/Moscow')
    cache.set(video_name, True, timeout=timeout)
    record = CachedVideo.objects.get(name=video_name)
    record.date_expire = datetime.datetime.now(tz=timezone) + datetime.timedelta(seconds=timeout)
    record.save()
