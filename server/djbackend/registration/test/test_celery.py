from django.test import TestCase
from ..tasks import aprove_user, check_nonactive, clean_denied
import socket
import queue
import threading
import json
from django.contrib.auth import get_user_model

User = get_user_model()

class TestAproveUser(TestCase):

    @classmethod
    def setUpClass(cls):

        def fake_server():
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(('127.0.0.1', 20900))
            server_sock.listen(10)
            server_sock.settimeout(1)
            signal = ''

            while signal != 'Stop':
                signal = cls.sig.get()

                try:
                    conn, addr = server_sock.accept()
                except TimeoutError:
                    pass
                else:
                    msg = conn.recv(1024).decode()
                    cls.result.put(msg)
                conn.close()

            server_sock.shutdown(socket.SHUT_RDWR)
            server_sock.close()


        cls.sig = queue.Queue()
        cls.result = queue.Queue()

        cls.th = threading.Thread(target=fake_server)
        cls.th.start()

        cls.test_user_1 = 'test_user_1'
        cls.test_password_1 = '1X<ISRUkw+tuK'
        cls.test_email_1 = 'email1@mail.ru'
        cls.test_user_2 = 'test_user_2'
        cls.test_password_2 = '1X<ISRUkw+tuK1'
        cls.test_email_2 = 'email2@mail.ru'
        test_user_1 = User.objects.create_user(username=cls.test_user_1,
                                             password=cls.test_password_1,
                                             email=cls.test_email_1,
                                             is_active=False,
                                             admin_checked=False,)
        test_user_2 = User.objects.create_user(username=cls.test_user_2,
                                               password=cls.test_user_2,
                                               email=cls.test_email_2,
                                               is_active=True,
                                               admin_checked=False)
        test_user_1.save()
        test_user_2.save()
        cls.request = {'request_type':'aprove_user_request', 
                       'username':cls.test_user_1,
                       'email':cls.test_email_1}

    @classmethod
    def tearDownClass(cls):
        cls.sig.put('Stop')
        cls.th.join()
        users = User.objects.all()
        for user in users:
            user.delete()

    def test_aprove_user_send_correct_message(self):
        self.sig.put('Test')
        user = User.objects.get(username=self.test_user_1)
        app = aprove_user.apply(args=(user,)).get()
        result = self.result.get()
        self.assertEqual(json.dumps(self.request), result)

    def test_check_nonactive_users(self):
        self.sig.put('Test')
        app = check_nonactive.apply().get()
        result = self.result.get()
        self.assertEqual(json.dumps(self.request), result)


class TestCleanDenied(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_user_1 = 'test_user_1'
        cls.test_password_1 = '1X<ISRUkw+tuK'
        cls.test_email_1 = 'email1@mail.ru'
        cls.test_user_2 = 'test_user_2'
        cls.test_password_2 = '1X<ISRUkw+tuK1'
        cls.test_email_2 = 'email2@mail.ru'
        test_user_1 = User.objects.create_user(username=cls.test_user_1,
                                             password=cls.test_password_1,
                                             email=cls.test_email_1,
                                             is_active=False,
                                             admin_checked=True,)
        test_user_2 = User.objects.create_user(username=cls.test_user_2,
                                               password=cls.test_user_2,
                                               email=cls.test_email_2,
                                               is_active=False,
                                               admin_checked=False,)
        test_user_1.save()
        test_user_2.save()

    def test_clean_denied_users(self):
        app = clean_denied.apply().get()
        users = User.objects.all()
        self.assertEqual(1, len(users))
        self.assertEqual(self.test_user_2, users[0].username)