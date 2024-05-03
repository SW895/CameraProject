import datetime
import pytz
import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from unittest.mock import Mock, patch
from ..models import ArchiveVideo, CachedVideo, Camera
from ..views import VideoDetailView


User = get_user_model()
timezone = pytz.timezone('Europe/Moscow')


class TestMainView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_user = 'test_user_1'
        cls.test_password = '1X<ISRUkw+tuK'
        test_user = User.objects.create_user(username=cls.test_user,
                                             password=cls.test_password,
                                             is_active=True,)
        test_user.save()

    def test_GET_anonymous_user(self):
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)

    def test_GET_authenticated_user(self):        
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(reverse('main'))
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)

    def test_view_accessible_by_name(self):
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('')
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('main'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main/main_page.html')


class TestStreamView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_user = 'test_user_1'
        cls.test_password = '1X<ISRUkw+tuK'
        test_user = User.objects.create_user(username=cls.test_user,
                                             password=cls.test_password,
                                             is_active=True,)
        test_user.save()
        cls.active_camera_id = Camera.objects.create(camera_name='active', is_active=True).pk
        cls.non_active_camera = Camera.objects.create(camera_name='non_active', is_active=False)

    def test_GET_anonymous_user(self):
        response = self.client.get(reverse('stream'))
        self.assertRedirects(response, '/accounts/login/?next=/stream/')

    def test_GET_authenticated_user(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(reverse('stream'))
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)

    def test_view_url_exists_at_desired_location(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get('/stream/')
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(reverse('stream'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertTemplateUsed(response, 'main/stream_page.html')
    
    def test_proper_camera_queryset(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(reverse('stream'))
        expected_camera_name = Camera.objects.get(id=self.active_camera_id)
        cam_list = [expected_camera_name.camera_name]
        expected_cam_list = json.dumps(cam_list)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.context['camera_list'][0].camera_name, expected_camera_name.camera_name)
        self.assertEqual(response.context['cam_list'], expected_cam_list)
        self.assertEqual(1, len(response.context['camera_list']))


class TestArchiveView(TestCase):
    @classmethod
    def setUp(cls):
        cls.test_user = 'test_user_1'
        cls.test_password = '1X<ISRUkw+tuK'
        cls.current_date = datetime.datetime.now(tz=timezone) + datetime.timedelta(days=100)
        cls.date_string = cls.current_date.strftime('%Y-%m-%d')
        test_user = User.objects.create_user(username=cls.test_user,
                                             password=cls.test_password,
                                             is_active=True,)
        test_user.save()  

        cls.test_video_pk = ArchiveVideo.objects.create(
                                    date_created=cls.current_date 
                                    - datetime.timedelta(days=10),
                                    human_det = False,
                                    chiken_det = False,
                                    cat_det = False,
                                    car_det = False
                                    ).pk
    
    def test_GET_anonymous_user(self):
        response = self.client.get(reverse('archive'))
        self.assertRedirects(response, '/accounts/login/?next=/archive/')

    def test_GET_authenticated_user(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(reverse('archive'))
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)

    def test_view_url_exists_at_desired_location(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get('/archive/')
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(reverse('archive'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertTemplateUsed(response, 'main/archive_page.html')

    def test_get_item_by_date(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(f'/archive?date_created={self.date_string}', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 0)
        test_video = ArchiveVideo.objects.get(pk=self.test_video_pk)
        test_video.date_created = self.current_date
        test_video.save()
        response = self.client.get(f'/archive?date_created={self.date_string}', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 1)

    def test_human_det_item(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get('/archive?human_det=True', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 0)
        test_video = ArchiveVideo.objects.get(pk=self.test_video_pk)
        test_video.human_det = True
        test_video.save()
        response = self.client.get('/archive?human_det=True', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 1)
    
    def test_chiken_det_item(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get('/archive?chiken_det=True', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 0)
        test_video = ArchiveVideo.objects.get(pk=self.test_video_pk)
        test_video.chiken_det = True
        test_video.save()
        response = self.client.get('/archive?chiken_det=True', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 1)
    
    def test_car_det_item(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get('/archive?car_det=True', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 0)
        test_video = ArchiveVideo.objects.get(pk=self.test_video_pk)
        test_video.car_det = True
        test_video.save()
        response = self.client.get('/archive?car_det=True', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 1)

    def test_cat_det_item(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get('/archive?cat_det=True', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 0)
        test_video = ArchiveVideo.objects.get(pk=self.test_video_pk)
        test_video.cat_det = True
        test_video.save()
        response = self.client.get('/archive?cat_det=True', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 1)
    
    def test_full_query(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(f'/archive?cat_det=True&car_det=True&chiken_det=True&human_det=True&date_created={self.date_string}', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 0)
        test_video = ArchiveVideo.objects.get(pk=self.test_video_pk)
        test_video.cat_det = True
        test_video.human_det = True
        test_video.car_det = True
        test_video.chiken_det = True
        test_video.date_created = self.current_date
        test_video.save()
        response = self.client.get(f'/archive?cat_det=True&car_det=True&chiken_det=True&human_det=True&date_created={self.date_string}', follow=True)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('videos' in response.context)
        self.assertEqual(len(response.context['videos']), 1)


class TestVideoDetailView(TestCase):    

    @classmethod
    def setUp(cls):
        cls.current_date = datetime.datetime.now(tz=timezone)
        cls.date_string = cls.current_date.strftime('%Y-%m-%d')
        cls.video_name = cls.current_date.strftime("%d_%m_%YT%H_%M_%S")
        cls.test_user = 'test_user_1'
        cls.test_password = '1X<ISRUkw+tuK'
        test_user = User.objects.create_user(username=cls.test_user,
                                             password=cls.test_password,
                                             is_active=True,)
        test_user.save()
        cls.test_video_pk = ArchiveVideo.objects.create(
                                    date_created=cls.current_date,
                                    human_det = False,
                                    chiken_det = False,
                                    cat_det = False,
                                    car_det = False
                                    ).pk        
        cls.test_object = VideoDetailView()
    
    @classmethod
    def tearDown(self):
        name = self.current_date.strftime("%d_%m_%YT%H_%M_%S")
        cache.delete(name)
        for item in CachedVideo.objects.all():
            item.delete()

    def test_get_context_data_request_video_with_cache(self):
        self.test_cached_video_pk = CachedVideo.objects.create(name = self.video_name,
                                                               date_expire = self.current_date + 
                                                               datetime.timedelta(days=10))        
        cache.set(self.video_name, True, timeout=60)
        with patch('main.views.VideoDetailView.request_video') as request:
            request.return_value = True
            self.client.login(username=self.test_user, password=self.test_password)
            response = self.client.get(f'/archive/{self.test_video_pk}')
            self.assertIn('video_name', response.context)
            self.assertIsNotNone(response.context['video_name'])
            request.assert_not_called()
    
    def test_call_update_cache(self):        
        self.test_cached_video_pk = CachedVideo.objects.create(name = self.video_name,
                                                               date_expire = self.current_date + 
                                                               datetime.timedelta(days=10))        
        cache.set(self.video_name, True, timeout=60)
        with patch('main.views.update_cache') as update_cache:
            self.client.login(username=self.test_user, password=self.test_password)
            response = self.client.get(f'/archive/{self.test_video_pk}')
            update_cache.assert_called_once()

    def test_get_context_data_success_request_video_without_cache(self):
        with patch('main.views.VideoDetailView.request_video') as request:
            request.return_value = True
            self.client.login(username=self.test_user, password=self.test_password)
            response = self.client.get(f'/archive/{self.test_video_pk}')
            self.assertIn('video_name', response.context)
            self.assertIsNotNone(response.context['video_name'])
            request.assert_called_once()

    def test_get_context_data_failure_request_video_without_cache(self):
        with patch('main.views.VideoDetailView.request_video') as request:
            request.return_value = False
            self.client.login(username=self.test_user, password=self.test_password)
            response = self.client.get(f'/archive/{self.test_video_pk}')
            self.assertIn('video_name', response.context)
            self.assertIsNone(response.context['video_name'])
            request.assert_called_once()
    
    def test_created_cache_records(self):
        self.assertEqual(0, len(CachedVideo.objects.all()))
        with patch('main.views.VideoDetailView.request_video') as request:
            request.return_value = True
            self.client.login(username=self.test_user, password=self.test_password)
            response = self.client.get(f'/archive/{self.test_video_pk}')
            self.assertEqual(1, len(CachedVideo.objects.all()))
    
    def test_GET_anonymous_user(self):
        with patch('main.views.VideoDetailView.request_video') as request:
            request.return_value = True
            response = self.client.get(f'/archive/{self.test_video_pk}', follow=True)
            self.assertRedirects(response, f'/accounts/login/?next=/archive/{self.test_video_pk}')

    def test_GET_authenticated_user(self):
        with patch('main.views.VideoDetailView.request_video') as request:
            request.return_value = True
            self.client.login(username=self.test_user, password=self.test_password)
            response = self.client.get(f'/archive/{self.test_video_pk}')
            self.assertEqual(str(response.context['user']), self.test_user)
            self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        with patch('main.views.VideoDetailView.request_video') as request:
            request.return_value = True
            self.client.login(username=self.test_user, password=self.test_password)
            response = self.client.get(f'/archive/{self.test_video_pk}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(str(response.context['user']), self.test_user)
            self.assertTemplateUsed(response, 'main/archivevideo_detail.html')

    def test_request_video_success(self):   
        mock_socket = Mock()
        VideoDetailView.connect_to_server = Mock(return_value=mock_socket)
        mock_socket.recv.return_value = b'success'
        response = self.test_object.request_video(video_name=self.video_name)
        self.assertTrue(response)
        mock_socket.recv.assert_called_once()

    def test_request_video_failure(self):
        mock_socket = Mock()
        VideoDetailView.connect_to_server = Mock(return_value=mock_socket)
        mock_socket.recv.return_value = b'failure'
        response = self.test_object.request_video(video_name=self.video_name)
        self.assertFalse(response)
        mock_socket.recv.assert_called_once()
