from django.test import TestCase
import sys
import configparser
from types import FunctionType
sys.path.insert(1, '/home/moreau/CameraProject/camera_app/')
from main_thread_ref import CameraClient, ClientRequest
from unittest.mock import Mock, patch
from django.conf import settings
import os


config = configparser.ConfigParser()
config.read('/home/moreau/CameraProject/camera_app/camera.ini')


class TestGetHandlers(TestCase):
    
    @classmethod
    def setUp(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
    
    def test_handlers_type(self):
        handlers = self.test_object.get_handlers()
        for item in handlers.values():
            self.assertIsInstance(item, FunctionType)

    def test_keys_list_not_empty(self):
        handlers = self.test_object.get_handlers()
        self.assertTrue(handlers.keys())

    def test_actual_handlers(self):
        actual_handlers = ['stop', 'stream', 
                           'video_request', 'user_aprove_request',
                           'corrupted_record'].sort()
        handlers = self.test_object.get_handlers()
        self.assertEqual(list(handlers.keys()).sort(), actual_handlers)


class TestSignalConnection(TestCase):

    @classmethod
    def setUp(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        for item in cls.test_object.handlers.keys():
            cls.test_object.handlers[item] = Mock(name=item)
        cls.test_object.get_connection = Mock(return_value=cls.mock_socket)

    def test_handler_stop_called_properly(self):
        request_type = 'stop'
        request = '{"request_type":"stop"}|'
        self.mock_socket.recv.return_value = request.encode()
        self.test_object.signal_connection()
        response = self.test_object.test_queue.get()
        self.test_object.handlers[request_type].assert_called_once()

    def test_handler_stream_called_properly(self):
        request_type = 'stream'
        request = '{"request_type":"stream"}|'
        self.mock_socket.recv.return_value = request.encode()
        self.test_object.signal_connection()
        response = self.test_object.test_queue.get()
        self.test_object.handlers[request_type].assert_called_once()

    def test_handler_video_request_called_properly(self):
        request_type = 'video_request'
        request = '{"request_type":"video_request"}|'
        self.mock_socket.recv.return_value = request.encode()
        self.test_object.signal_connection()
        response = self.test_object.test_queue.get()
        self.test_object.handlers[request_type].assert_called_once()

    def test_handler_user_aprove_request_called_properly(self):
        request_type = 'user_aprove_request'
        request = '{"request_type":"user_aprove_request"}|'
        self.mock_socket.recv.return_value = request.encode()
        self.test_object.signal_connection()
        response = self.test_object.test_queue.get()
        self.test_object.handlers[request_type].assert_called_once()

    def test_handler_corrupted_record_called_properly(self):
        request_type = 'corrupted_record'
        request = '{"request_type":"corrupted_record"}|'
        self.mock_socket.recv.return_value = request.encode()
        self.test_object.signal_connection()
        response = self.test_object.test_queue.get()
        self.test_object.handlers[request_type].assert_called_once()

    def test_wrong_request_type(self):
        request_type = 'aaa'
        request = '{"request_type":"aaa"}|'
        self.mock_socket.recv.return_value = request.encode()
        self.test_object.signal_connection()
        response = self.test_object.test_queue.get()
        self.assertEqual('Wrong request', response)


class TestHandlerStop(TestCase):

    @classmethod
    def setUp(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
    
    def test_signal_queue(self):
        request = ClientRequest(request_type='stop')
        self.test_object.handler_stop(request)
        response = self.test_object.signal_queue.get()
        self.assertEqual(response, request)


class TestHandlerCorruptedRecord(TestCase):

    @classmethod
    def setUp(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
    
    @classmethod
    def tearDown(cls):
        if os.path.exists('db.json'):
            os.remove('db.json')

    def test_records_saved_to_file(self):
        request = ClientRequest(request_type='corrupted_record',
                                db_record='{"222":"111"}')
        self.test_object.handler_corrupted_record(request)
        response = self.test_object.test_queue.get()
        self.assertTrue(os.path.exists('db.json'))
        with open('db.json', 'r') as file:
            line = file.readline()
            self.assertEqual(request.db_record + '\n', line)


class TestHandlerStream(TestCase):

    @classmethod
    def setUp(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        cls.test_object.convert_frame = Mock(return_value=b'test')
        cls.request = ClientRequest(request_type='stream')
    
    def test_get_connection_called(self):
        self.test_object.get_connection = Mock(return_value=None)
        self.test_object.handler_stream(self.request)   
        resposne = self.test_object.test_queue.get()     
        self.test_object.get_connection.assert_called_once()

    def test_frame_send(self):
        self.test_object.get_connection = Mock(return_value=self.mock_socket)        
        self.test_object.frame_queue.put(b'test')
        self.test_object.signal_queue.put(ClientRequest(request_type='stop'))
        self.test_object.handler_stream(self.request)
        response = self.test_object.test_queue.get()
        self.test_object.convert_frame.assert_called_once_with(b'test')
        self.mock_socket.sendall.assert_called_once()

    def test_stop_stream_by_signal(self):
        self.test_object.get_connection = Mock(return_value=self.mock_socket)        
        self.test_object.frame_queue.put(b'test')
        self.test_object.signal_queue.put(ClientRequest(request_type='stop'))
        self.test_object.handler_stream(self.request)
        response = self.test_object.test_queue.get()
        self.assertEqual(response, 'stop')


class TestHandlerUserAproveRequest(TestCase):

    @classmethod
    def setUp(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.test_object.get_connection = Mock()
        cls.test_object.send_email = Mock()
        cls.request = ClientRequest(request_type='aprove_user_request',
                                    username='username',
                                    email='test@mail.ru')
        
    def test_aprove_user(self):
        self.test_object.handler_user_aprove_request(self.request)
        self.test_object.APROVE_ALL = True
        response = self.test_object.test_queue.get()
        self.test_object.get_connection.assert_called_once_with(ClientRequest(request_type='user_aprove_response',
                                                            username='username',
                                                            request_result='aproved'))
        self.test_object.send_email.assert_called_with('username','test@mail.ru', True)

    def test_deny_user(self):
        self.test_object.handler_user_aprove_request(self.request)
        self.test_object.APROVE_ALL = False
        response = self.test_object.test_queue.get()
        self.test_object.get_connection.assert_called_once_with(ClientRequest(request_type='user_aprove_response',
                                                            username='username',
                                                            request_result='denied'))
        self.test_object.send_email.assert_called_with('username','test@mail.ru', False)

class TestHandlerVideoRequest(TestCase):
    @classmethod
    def setUp(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        cls.test_object.get_connection = Mock(return_value=cls.mock_socket)
        cls.request = ClientRequest(request_type='video_request',
                                    video_name='2021-04-23T14:12:12',)
        cls.wrong_request = ClientRequest(request_type='video_request',
                                    video_name='2023-04-23T14:12:12',)
        cls.save_path = cls.test_object.save_path / (cls.request.video_name.split('T')[0])
        cls.video_name = cls.save_path / (cls.request.video_name + '.mp4')
        cls.video_size = 125000
        if not os.path.isdir(cls.save_path):
            os.mkdir(cls.save_path)
        with open(cls.video_name, 'wb') as video:
            video.write(bytes(cls.video_size))

    @classmethod
    def tearDown(cls):
        if os.path.exists(cls.video_name):
            os.remove(cls.video_name)
        os.rmdir(cls.save_path)

    def test_video_response(self):
        self.test_object.handler_video_request(self.request)
        response = self.test_object.test_queue.get()
        self.test_object.get_connection.assert_called_once_with(ClientRequest(request_type='video_response',
                                           video_name='2021-04-23T14:12:12',
                                           video_size=str(self.video_size)))
        self.mock_socket.sendall.assert_called_once_with(bytes(self.video_size))
    
    def test_no_video_in_storage(self):
        self.test_object.handler_video_request(self.wrong_request)
        response = self.test_object.test_queue.get()
        self.assertEqual(response, 'no such video')

"""
class TestSendEmail(TestCase):
    pass

class TestCameraThread(TestCase):
    pass

class TestSaveVideo(TestCase):
    pass
    
"""