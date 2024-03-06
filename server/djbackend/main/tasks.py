from djbackend.celery import app
from django.core.cache import cache
from django.conf import settings
from .models import CachedVideo
import datetime
import os


@app.task
def clean_expired_records():
    records = CachedVideo.objects.filter(date_expire__lt=datetime.datetime.now())
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
    cache.set(video_name, True, timeout=timeout)
    record = CachedVideo.objects.get(name=video_name)
    record.date_expire = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
    record.save()
