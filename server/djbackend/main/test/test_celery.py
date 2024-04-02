from django.test import TestCase
from ..models import CachedVideo
import datetime
from ..tasks import clean_expired_records, clean_video, update_cache
from django.conf import settings
import os
from django.core.cache import cache
import time
import pytz

timezone = pytz.timezone('Europe/Moscow')

class TestCleanExpiredRecords(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.expire_id = CachedVideo.objects.create(name='expired_record',
                                   date_expire=datetime.datetime.now(tz=timezone) -
                                               datetime.timedelta(days=100)).pk
        cls.actual_id = CachedVideo.objects.create(name='actual_record',
                                   date_expire=datetime.datetime.now(tz=timezone) +
                                   datetime.timedelta(days=100)).pk
        
        cls.expired_name = str(settings.MEDIA_ROOT) + '/' + 'expired_record' + '.mp4'
        expired = open(cls.expired_name, 'w')
        expired.close()

        cls.actual_name = str(settings.MEDIA_ROOT) + '/' + 'actual_record' + '.mp4'
        actual = open(cls.actual_name, 'w')
        actual.close()

    @classmethod
    def tearDown(self):
        if os.path.exists(self.expired_name):
            os.remove(self.expired_name)
        if os.path.exists(self.actual_name):
            os.remove(self.actual_name)

    def test_expired_record_delete(self):
        result = clean_expired_records.apply().get()
        self.assertFalse(CachedVideo.objects.filter(id=self.expire_id).exists())

    def test_expired_record_file_delete(self):
        result = clean_expired_records.apply().get()
        self.assertFalse(os.path.exists(self.expired_name))
    
    def test_actual_record_no_delete(self):
        result = clean_expired_records.apply().get()
        self.assertTrue(CachedVideo.objects.filter(id=self.actual_id).exists())

    def test_actual_file_no_delete(self):
        result = clean_expired_records.apply().get()
        self.assertTrue(os.path.exists(self.actual_name))


class TestCleanVideo(TestCase):

    @classmethod
    def setUpTestData(cls):        
        cls.actual_id = CachedVideo.objects.create(name='actual_video',
                                   date_expire=datetime.datetime.now(tz=timezone)).pk
        
        cls.actual_name = str(settings.MEDIA_ROOT) + '/' + 'actual_video' + '.mp4'
        actual = open(cls.actual_name, 'w')
        actual.close()

        cls.lost_name = str(settings.MEDIA_ROOT) + '/' + 'lost_video' + '.mp4'
        lost_file = open(cls.lost_name, 'w')
        lost_file.close()

    @classmethod
    def tearDown(self):
        if os.path.exists(self.lost_name):
            os.remove(self.lost_name)
        if os.path.exists(self.actual_name):
            os.remove(self.actual_name)


    def test_delete_lost_files(self):
        result = clean_video.apply().get()
        self.assertFalse(os.path.exists(self.lost_name))

    def test_actual_file_no_delete(self):
        result = clean_video.apply().get()
        self.assertTrue(os.path.exists(self.actual_name))

    
class TestUpdateCache(TestCase):
    
    @classmethod
    def setUpTestData(cls):
        cls.timeout = 1
        cls.video_name = 'test_video'
        cls.date_expire = datetime.datetime.now(tz=timezone)
        cache.set(cls.video_name, True, timeout=1)
        cls.cache_pk = CachedVideo.objects.create(name=cls.video_name, 
                                                  date_expire=cls.date_expire).pk

    def test_cache_update_correctly(self):
        result = update_cache.apply(args=(self.video_name, self.timeout)).get()
        self.assertTrue(cache.get(self.video_name))
        time.sleep(self.timeout)
        self.assertFalse(cache.get(self.video_name))
        db_date_expire = CachedVideo.objects.get(pk=self.cache_pk).date_expire
        self.assertEqual(self.date_expire.second + datetime.timedelta(seconds=self.timeout).seconds, 
                         db_date_expire.second)
