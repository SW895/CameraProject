from django.test import TestCase
from ..models import ArchiveVideo, CachedVideo, Camera
import datetime
import pytz

timezone = pytz.timezone('Europe/Moscow')


class TestArchiveVideo(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.obj_id = ArchiveVideo.objects.create(
            date_created=datetime.datetime.now(tz=timezone)
        ).pk

    def test_cat_det_false_by_default(self):
        video = ArchiveVideo.objects.get(id=self.obj_id)
        self.assertFalse(video.cat_det)

    def test_car_det_false_by_default(self):
        video = ArchiveVideo.objects.get(id=self.obj_id)
        self.assertFalse(video.car_det)

    def test_chicken_det_false_by_default(self):
        video = ArchiveVideo.objects.get(id=self.obj_id)
        self.assertFalse(video.chiken_det)

    def test_human_det_false_by_dafult(self):
        video = ArchiveVideo.objects.get(id=self.obj_id)
        self.assertFalse(video.human_det)

    def test_string_representation(self):
        video = ArchiveVideo.objects.get(id=self.obj_id)
        expected_name = str(video.date_created)
        self.assertEqual(str(video), expected_name)


class TestCachedVideo(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.obj_id = CachedVideo.objects.create(
            name='2024-02-02T14:25:34',
            date_expire=datetime.datetime.now(tz=timezone)
        ).pk

    def test_string_representation(self):
        cached_video = CachedVideo.objects.get(id=self.obj_id)
        expected_name = '2024-02-02T14:25:34'
        self.assertEqual(str(cached_video), expected_name)

    def test_name_length(self):
        cached_video = CachedVideo.objects.get(id=self.obj_id)
        max_length = cached_video._meta.get_field('name').max_length
        self.assertEqual(max_length, 100)


class TestCamera(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.obj_id = 'test'
        Camera.objects.create(camera_name='test')

    def test_is_active_false_by_default(self):
        camera = Camera.objects.get(camera_name=self.obj_id)
        self.assertFalse(camera.is_active)

    def test_string_representation(self):
        camera = Camera.objects.get(camera_name=self.obj_id)
        expected_name = 'test'
        self.assertEqual(str(camera), expected_name)
