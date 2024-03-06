from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import ArchiveVideo, CachedVideo
import datetime
import socket, threading
import queue
from django.core.cache import cache

User = get_user_model()
 
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


class TestCameraSourceView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_user = 'test_user_1'
        cls.test_password = '1X<ISRUkw+tuK'
        test_user = User.objects.create_user(username=cls.test_user,
                                             password=cls.test_password,
                                             is_active=True,)
        test_user.save()

    def test_GET_anonymous_user(self):
        response = self.client.get(reverse('camera-source'))
        self.assertRedirects(response, '/accounts/login/?next=/camera_source/')

    def test_GET_authenticated_user(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(reverse('camera-source'), follow=True)
        #self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)

    def test_view_url_exists_at_desired_location(self):
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get('/camera_source/', follow=True)
        #self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)


class TestArchiveView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_user = 'test_user_1'
        cls.test_password = '1X<ISRUkw+tuK'
        cls.current_date = datetime.datetime.now()
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
    def tearDown(self):
        name = self.current_date.strftime("%d_%m_%YT%H_%M_%S")
        cache.delete(name)
        for item in CachedVideo.objects.all():
            item.delete()

    @classmethod
    def setUpClass(cls):

        def fake_server():
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(('127.0.0.1', 20900))
            server_sock.listen(10)
            server_sock.settimeout(1)
            signal = 'TestS'
            
            while signal != 'Stop':
                signal = cls.sig.get()
                if signal == 'TestCache':
                    continue
                try:
                    conn, addr = server_sock.accept()
                except TimeoutError:
                    pass
                else:
                    if signal == 'TestF':
                        reply = 'Failure'
                    else:
                        reply = 'Success'
                    msg = conn.recv(1024)
                    conn.send(reply.encode())
                    conn.close()
            
            server_sock.shutdown(socket.SHUT_RDWR)
            server_sock.close()


        cls.sig = queue.Queue()
        cls.th = threading.Thread(target=fake_server)
        cls.th.start()

        cls.test_user = 'test_user_1'
        cls.test_password = '1X<ISRUkw+tuK'
        cls.current_date = datetime.datetime.now()
        cls.date_string = cls.current_date.strftime('%Y-%m-%d')
        cls.video_name = cls.current_date.strftime("%d_%m_%YT%H_%M_%S")
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


    @classmethod
    def tearDownClass(cls):
        cls.sig.put('Stop')
        cls.th.join()

    def test_GET_anonymous_user(self):
        response = self.client.get(f'/archive/{self.test_video_pk}', follow=True)
        self.assertRedirects(response, f'/accounts/login/?next=/archive/{self.test_video_pk}')

    def test_GET_authenticated_user(self):
        self.sig.put('TestS')
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(f'/archive/{self.test_video_pk}')
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        self.sig.put('TestS')        
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(f'/archive/{self.test_video_pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context['user']), self.test_user)
        self.assertTemplateUsed(response, 'main/archivevideo_detail.html')

    def test_success_without_cache(self):
        self.sig.put('TestS')
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(f'/archive/{self.test_video_pk}')
        self.assertIn('video_name', response.context)
        self.assertIsNotNone(response.context['video_name'])

    def test_success_with_cache(self):
        self.sig.put('TestCache')
        self.test_cached_video_pk = CachedVideo.objects.create(name = self.video_name,
                                                               date_expire = self.current_date + 
                                                               datetime.timedelta(days=10))        
        cache.set(self.video_name, True, timeout=60)
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(f'/archive/{self.test_video_pk}')
        self.assertIn('video_name', response.context)
        self.assertIsNotNone(response.context['video_name'])
 
    def test_failure_without_cache(self):
        self.sig.put('TestF')
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(f'/archive/{self.test_video_pk}')
        self.assertIn('video_name', response.context)
        self.assertIsNone(response.context['video_name'])

    def test_correctly_add_item_to_cache(self):
        self.sig.put('TestS')
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(f'/archive/{self.test_video_pk}')
        self.assertTrue(cache.get(self.video_name))
    
    def test_correctly_add_item_to_CachedVideo_model(self):
        self.sig.put('TestS')
        self.client.login(username=self.test_user, password=self.test_password)
        response = self.client.get(f'/archive/{self.test_video_pk}')
        self.assertEqual(1, len(CachedVideo.objects.all()))
