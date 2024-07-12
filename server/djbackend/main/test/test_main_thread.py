import sys
import configparser
import os
import json
import time
import pytz
from datetime import date, datetime
from django.test import TestCase
from types import FunctionType
from pathlib import Path
from unittest.mock import Mock, patch


base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(1, str(base_dir) + '/camera_app/')
from main_thread import CameraClient, ClientRequest, CameraSource


config = configparser.ConfigParser()
config.read(base_dir / 'camera_app/camera.ini')


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
        actual_handlers = ['stream', 
                           'video_request', 'aprove_user_request',
                           'corrupted_record'].sort()
        handlers = self.test_object.get_handlers()
        self.assertEqual(list(handlers.keys()).sort(), actual_handlers)


class TestSignalConnection(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        for item in cls.test_object.handlers.keys():
            cls.test_object.handlers[item] = Mock(name=item)
    
    @classmethod
    def tearDownClass(cls):
        pass

    def tearDown(self):
        for item in self.test_object.handlers.keys():
            self.test_object.handlers[item].reset_mock()

    @patch('main_thread.get_connection')
    def test_handler_stream_called_properly(self, get_connection):
        get_connection.return_value = self.mock_socket
        request_type = 'stream'
        request = '{"request_type":"stream"}|'
        self.mock_socket.recv.return_value = request.encode()
        thread = self.test_object.signal_connection()
        thread.join()
        self.test_object.handlers[request_type].assert_called_once()

    @patch('main_thread.get_connection')
    def test_handler_video_request_called_properly(self, get_connection):
        get_connection.return_value = self.mock_socket
        request_type = 'video_request'
        request = '{"request_type":"video_request"}|'
        self.mock_socket.recv.return_value = request.encode()
        thread = self.test_object.signal_connection()
        thread.join()
        self.test_object.handlers[request_type].assert_called_once()

    @patch('main_thread.get_connection')
    def test_handler_user_aprove_request_called_properly(self, get_connection):
        get_connection.return_value = self.mock_socket
        request_type = 'aprove_user_request'
        request = '{"request_type":"aprove_user_request"}|'
        self.mock_socket.recv.return_value = request.encode()
        thread = self.test_object.signal_connection()
        thread.join()
        self.test_object.handlers[request_type].assert_called_once()

    @patch('main_thread.get_connection')
    def test_handler_corrupted_record_called_properly(self, get_connection):
        get_connection.return_value = self.mock_socket
        request_type = 'corrupted_record'
        request = '{"request_type":"corrupted_record"}|'
        self.mock_socket.recv.return_value = request.encode()
        thread = self.test_object.signal_connection()
        thread.join()
        self.test_object.handlers[request_type].assert_called_once()

    @patch('main_thread.get_connection')
    def test_wrong_request_type(self, get_connection):
        get_connection.return_value = self.mock_socket
        request = '{"request_type":"aaa"}|'
        self.mock_socket.recv.return_value = request.encode()
        thread = self.test_object.signal_connection()
        thread.join()
        for item in self.test_object.handlers.keys():
            self.test_object.handlers[item].assert_not_called()


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
        self.assertTrue(os.path.exists('db.json'))
        with open('db.json', 'r') as file:
            line = file.readline()
            self.assertEqual(request.db_record + '\n', line)


class TestHandlerUserAproveRequest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.test_object.send_email = Mock()
        cls.request = ClientRequest(request_type='aprove_user_request',
                                    username='username',
                                    email='test@mail.ru')
    
    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def tearDown(self):
        self.test_object.send_email.reset_mock()

    @patch('main_thread.get_connection')
    def test_aprove_user(self, get_connection):        
        self.test_object.APROVE_ALL = True
        thread = self.test_object.handler_aprove_user_request(self.request)
        thread.join()
        name, args, kwargs = get_connection.mock_calls[0]
        self.assertEqual(args, (ClientRequest(request_type='user_aprove_response',
                                                            username='username',
                                                            request_result='aproved'), ))
        self.test_object.send_email.assert_called_with('username','test@mail.ru', True)

    @patch('main_thread.get_connection')
    def test_deny_user(self, get_connection):
        self.test_object.APROVE_ALL = False
        thread = self.test_object.handler_aprove_user_request(self.request)
        thread.join()
        name, args, kwargs = get_connection.mock_calls[0]
        self.assertEqual(args, (ClientRequest(request_type='user_aprove_response',
                                                            username='username',
                                                            request_result='denied'), ))
        self.test_object.send_email.assert_called_with('username','test@mail.ru', False)


class TestHandlerVideoRequest(TestCase):

    @classmethod
    def setUp(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        cls.video_name = '2021-04-23T14:12:12'
        cls.request = ClientRequest(request_type='video_request',
                                    video_name='2021-04-23T14:12:12|test',)
        cls.wrong_request = ClientRequest(request_type='video_request',
                                    video_name='2023-04-23T14:12:12|test',)
        cls.camera_path = cls.test_object.save_path / 'test/'
        cls.save_path = cls.camera_path / (cls.video_name.split('T')[0])
        cls.full_video_name = cls.save_path / (cls.video_name + '.mp4')
        cls.video_size = 125000
        if not os.path.isdir(cls.camera_path):
            os.mkdir(cls.camera_path)
        if not os.path.isdir(cls.save_path):
            os.mkdir(cls.save_path)
        with open(cls.full_video_name, 'wb') as video:
            video.write(bytes(cls.video_size))

    @classmethod
    def tearDown(cls):
        cls.mock_socket.reset_mock()
        if os.path.exists(cls.full_video_name):
            os.remove(cls.full_video_name)
        os.rmdir(cls.save_path)
        os.rmdir(cls.camera_path)

    @patch('main_thread.get_connection')
    def test_video_response(self, get_connection):
        get_connection.return_value = self.mock_socket
        thread = self.test_object.handler_video_request(self.request)
        thread.join()
        name, args, kwargs = get_connection.mock_calls[0]
        self.assertEqual(args, (ClientRequest(request_type='video_response',
                                           video_name='2021-04-23T14:12:12|test',
                                           video_size=str(self.video_size)), ))
        self.mock_socket.sendall.assert_called_once_with(bytes(self.video_size))

    @patch('main_thread.get_connection')
    def test_no_video_in_storage(self, get_connection):
        thread = self.test_object.handler_video_request(self.wrong_request)
        thread.join()
        name, args, kwargs = get_connection.mock_calls[0]
        self.assertEqual(args, (ClientRequest(request_type='video_response',
                                           video_name='2021-04-23T14:12:12|test',
                                           video_size=0), ))


class TestRunClient(TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.test_object.get_camera_sources = Mock()
        cls.test_object.init_camera = Mock()
        cls.test_object.signal_connection = Mock()
    
    @classmethod
    def tearDownClass(cls):
        pass

    def test_function(self):
        self.test_object.run_client()
        self.test_object.get_camera_sources.assert_called_once()
        self.test_object.init_camera.assert_called_once()
        self.test_object.signal_connection.assert_called_once()


class TestInitCamera(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        cls.test_object.camera_sources = {'test_camera':CameraSource('0','test_camera')}
        cls.test_object.camera_sources['test_camera'].camera_thread = Mock()
    
    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(cls.test_object.camera_sources['test_camera'].save_path):
            os.rmdir(cls.test_object.camera_sources['test_camera'].save_path)
    
    @patch('main_thread.get_connection')
    def test_get_connection_called(self, get_connection):
        self.test_object.init_camera()
        get_connection.assert_called()

    @patch('main_thread.get_connection')
    def test_send_camera_info(self, get_connection):
        get_connection.return_value = self.mock_socket
        self.test_object.init_camera()
        record = json.dumps({'camera_name':'test_camera'}) + "\n"
        self.mock_socket.send.assert_called_with(record.encode())
    
    @patch('main_thread.get_connection')
    def test_starting_camera_thread(self, get_connection):
        self.test_object.init_camera()
        self.test_object.camera_sources['test_camera'].camera_thread.assert_called()


class TestHandlerStream(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.test_object.videostream_manager = Mock()
        cls.request = ClientRequest(request_type='stream', camera_name='test_camera')

    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_stream_queue(self):
        self.test_object.handler_stream(self.request)
        response = self.test_object.stream_request_queue.get()
        self.assertEqual(response, self.request)
        self.test_object.videostream_manager.assert_called()


class TestVideoStreamManager(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = CameraClient(config)
        cls.test_object.DEBUG = True
        cls.test_object.camera_sources = {'test_camera':CameraSource('0','test_camera')}
        cls.test_object.camera_sources['test_camera'].kill_thread = Mock()
        cls.test_object.camera_sources['test_camera'].run_thread = Mock()
        cls.test_object.replicator = Mock()
        cls.request = ClientRequest(request_type='stream', camera_name='test_camera')

    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(cls.test_object.camera_sources['test_camera'].save_path):
            os.rmdir(cls.test_object.camera_sources['test_camera'].save_path)

    def test_starting_new_videostream_thread(self):
        thread = self.test_object.videostream_manager()
        self.test_object.stream_request_queue.put(self.request)
        self.test_object.kill_videostream_manager()
        thread.join()
        self.test_object.camera_sources['test_camera'].kill_thread.assert_called_once()
        self.test_object.camera_sources['test_camera'].run_thread.assert_called_once()


class TestVideoStream(TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.camera_name = 'test'
        cls.test_object = CameraSource(cls.camera_name, cls.camera_name)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        cls.test_object.frame_queue = Mock()
        cls.test_object.frame_queue.get.return_value = b'frame'
        cls.test_object.convert_frame = Mock(return_value=b'frame')

    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(cls.test_object.save_path):
            os.rmdir(cls.test_object.save_path)

    @patch('main_thread.get_connection')
    def test_get_connection_called(self, get_connection):
        request = ClientRequest(request_type='stream', camera_name=self.camera_name)
        get_connection.return_value = self.mock_socket
        self.test_object.run_thread()
        time.sleep(0.5)
        self.test_object.kill_thread()
        name, args, kwargs = get_connection.mock_calls[0]
        self.assertEqual(args, (request, ))

    @patch('main_thread.get_connection')
    def test_convert_frame_called(self, get_connection):
        get_connection.return_value = self.mock_socket
        self.test_object.run_thread()
        time.sleep(0.5)
        self.test_object.kill_thread()
        self.test_object.convert_frame.assert_called()

    @patch('main_thread.get_connection')
    def test_send_data(self, get_connection):
        get_connection.return_value = self.mock_socket
        self.test_object.run_thread()
        time.sleep(0.5)
        self.test_object.kill_thread()
        self.mock_socket.sendall.assert_called()


class TestSaveVideo(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.camera_name = 'test'
        cls.test_object = CameraSource(cls.camera_name, cls.camera_name)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        cls.today = date.today()
        cls.timezone = pytz.timezone('Europe/Moscow')
        cls.current_date = datetime.now(tz=cls.timezone)
        cls.frames_to_save = ['test', 'test', 'test']
        cls.save_path = cls.test_object.save_path / (cls.today.strftime("%d_%m_%Y") + '/')
        cls.excpected_record = {            
            'car_det':True,
            'cat_det':False,
            'chiken_det':True,
            'human_det':True,
            'date_created': cls.current_date.isoformat(),
            'camera_id':'test',
        }
        cls.new_record = {
            'car_det':True,
            'cat_det':False,
            'chiken_det':True,
            'human_det':True,
        }

    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(cls.save_path):
            os.rmdir(cls.save_path)
        if os.path.isdir(cls.test_object.save_path):
            os.rmdir(cls.test_object.save_path)
        if os.path.exists(cls.test_object.base_dir / 'test.json'):
            os.remove(cls.test_object.base_dir / 'test.json')

    @patch('main_thread.torchvision')
    @patch('main_thread.get_connection')
    def test_save_video(self, get_connection, torch):
        get_connection.return_value = self.mock_socket
        self.mock_socket.send.side_effect = None
        thread = self.test_object.save_video(self.frames_to_save, self.new_record, self.current_date)
        thread.join()
        torch.io.write_video.assert_called()

    @patch('main_thread.torchvision')
    @patch('main_thread.get_connection')
    def test_record_sended_to_server(self, get_connection, torch):
        get_connection.return_value = self.mock_socket
        self.mock_socket.send.side_effect = None
        thread = self.test_object.save_video(self.frames_to_save, self.new_record, self.current_date)
        thread.join()
        self.mock_socket.send.assert_called_with(json.dumps(self.excpected_record).encode())

    @patch('main_thread.torchvision')
    @patch('main_thread.get_connection')
    def test_fail_to_send_new_record(self, get_connection, torch):
        get_connection.return_value = self.mock_socket
        self.mock_socket.send.side_effect = BrokenPipeError
        thread = self.test_object.save_video(self.frames_to_save, self.new_record, self.current_date)
        thread.join()
        self.assertTrue(os.path.exists(self.test_object.base_dir / 'test.json'))
        with open((self.test_object.base_dir / 'test.json'), 'r') as outfile:
            line = outfile.readline()
        self.assertEqual(line, json.dumps(self.excpected_record) +'\n')