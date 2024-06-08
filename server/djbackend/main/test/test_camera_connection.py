import json
import threading
import sys
import datetime
import os
import pytz
import time
from django.test import TestCase
from unittest.mock import Mock, patch
from types import FunctionType
from django.contrib.auth import get_user_model
from pathlib import Path
from ..models import ArchiveVideo, Camera

base_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(1, str(base_dir) + '/camera_conn/')
from camera_conn import EchoServer, StreamChannel, ServerRequest

test_adress = '127.0.0.1'
test_port_1 = 20900
test_port_2 = 10900
timezone = pytz.timezone('Europe/Moscow')
User = get_user_model()


class TestListHandlers(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_proper_handler_list(self):
        actual = self.test_object.list_handlers()
        expected = 'External request types:\nsignal\nnew_record\nvideo_response\nuser_aprove_response\nstream_source\nInternal request types:\naprove_user_request\nvideo_request\nstream_request'
        self.assertEqual(actual, expected)


class TestGetHandlers(TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_external_handlers_type(self):
        handlers = self.test_object.get_EHandlers()
        for item in handlers.values():
            self.assertIsInstance(item, FunctionType)

    def test_external_keys_list_not_empty(self):
        handlers = self.test_object.get_EHandlers()
        self.assertTrue(handlers.keys())

    def test_external_actual_handlers(self):
        actual_handlers = ['signal', 'stream_source', 'new_record', 
                            'video_response', 'user_aprove_response'].sort()
        handlers = self.test_object.get_EHandlers()
        self.assertEqual(list(handlers.keys()).sort(), actual_handlers)
    
    def test_internal_handlers_type(self):
        handlers = self.test_object.get_IHandlers()
        for item in handlers.values():
            self.assertIsInstance(item, FunctionType)

    def test_internal_keys_list_not_empty(self):
        handlers = self.test_object.get_IHandlers()
        self.assertTrue(handlers.keys())

    def test_internal_actual_handlers(self):
        actual_handlers = ['aprove_user_request', 'stream_request', 'video_request'].sort()
        handlers = self.test_object.get_IHandlers()
        self.assertEqual(list(handlers.keys()).sort(), actual_handlers)


class TestRunServer(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.test_object.run_external_server = Mock()
        cls.test_object.run_internal_server = Mock()
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    @patch('socket.socket')
    def test_create_server_threads(self, sock):
        self.test_object.run_server()
        self.test_object.run_external_server.assert_called_once()
        self.test_object.run_internal_server.assert_called_once()


class TestRunExternalServer(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.address = test_adress
        cls.reply = 'accepted'
        for item in cls.test_object.external_handlers.keys():
            cls.test_object.external_handlers[item] = Mock(name=item)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_signal_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'signal'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()

    def test_stream_source_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'stream_source'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()

    def test_new_record_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'new_record'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()

    def test_video_response_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'video_response'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()
    
    def test_user_aprove_handler(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'user_aprove_response'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()

    def test_wrong_request_type(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'wrong_signal'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
        mock_socket.close.assert_called_once()


class TestRunInternalServer(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.address = test_adress
        for item in cls.test_object.internal_handlers.keys():
            cls.test_object.internal_handlers[item] = Mock(name=item)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_aprove_user_request_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'aprove_user_request'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_internal_server(mock_socket)
            thread.join()
        self.test_object.internal_handlers[request['request_type']].assert_called_once()

    def test_video_request_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'video_request'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_internal_server(mock_socket)
            thread.join()
        self.test_object.internal_handlers[request['request_type']].assert_called_once()

    def test_steam_request_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'stream_request'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_internal_server(mock_socket)
            thread.join()
        self.test_object.internal_handlers[request['request_type']].assert_called_once()

    def test_wrong_request_type(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.address)
            request = {'request_type':'wrong_signal'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_internal_server(mock_socket)
            thread.join()
        mock_socket.close.assert_called_once()


class TestHandlerSignal(TestCase):
    
    @classmethod
    def setUpClass(cls):       
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.request = ServerRequest(request_type='signal',connection=Mock(), address=test_adress)
        cls.test_object.check_connection = Mock()
        cls.test_signal = ServerRequest(request_type='test')
    
    @classmethod
    def tearDownClass(cls):
        pass

    def test_check_tread_started(self):
        thread = self.test_object.ehandler_signal(self.request)
        self.test_object.signal_queue.put(self.test_signal)
        th_running = False
        for th in threading.enumerate():
            if th.name == 'ehandler_signal':
                th_running = True
                break
        self.assertTrue(th_running)
        thread.join()

    def test_sending_signal_to_client(self):
        thread = self.test_object.ehandler_signal(self.request)
        self.test_object.signal_queue.put(self.test_signal)
        expected_msg = json.dumps(self.test_signal.__dict__) + '|'
        thread.join()
        self.request.connection.send.assert_called_with(expected_msg.encode())

    def test_restart_signal(self):
        thread = self.test_object.ehandler_signal(self.request)
        th_running = False
        for th in threading.enumerate():
            if th.name == 'ehandler_signal':
                th_running = True
                break
        self.assertTrue(th_running)
        self.test_object.signal_queue.put(ServerRequest(request_type='restart'))
        thread.join()      
        th_running = False
        for th in threading.enumerate():
            if th.name == 'ehandler_signal':
                th_running = True
                break
        self.assertFalse(th_running)


class TestHandlerNewRecord(TestCase):

    @classmethod
    def setUpClass(cls):       
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.test_object.save_record = Mock()
        cls.test_object.save_or_update_camera = Mock()
        cls.time_1 = datetime.datetime.now(tz=timezone)
        cls.time_2 = datetime.datetime.now(tz=timezone) + datetime.timedelta(days=10)
        cls.record_1 = {'date_created': cls.time_1.isoformat(), 
                      'human_det':False,
                      'cat_det':False,
                      'car_det':False,
                      'chiken_det':False}
        cls.record_2 = {'date_created':cls.time_2.isoformat(), 
                      'human_det':False,
                      'cat_det':False,
                      'car_det':False,
                      'chiken_det':False}
        cls.camera_record = {'camera_name':'test'}
        cls.test_request_video_record = ServerRequest(request_type='new_record',
                                                      db_record='aaa',
                                                      connection=Mock())
        cls.test_request_camera = ServerRequest(request_type='new_record',
                                                      camera_name='aaa',
                                                      connection=Mock())

    @classmethod
    def tearDownClass(cls):
        pass

    def test_receive_single_record(self):
        self.test_request_video_record.connection.recv.return_value = json.dumps(self.record_1).encode()
        thread = self.test_object.ehandler_new_record(self.test_request_video_record)
        response = self.test_object.save_db_records_queue.get()
        self.assertEqual(self.record_1, response)
        thread.join()
        self.test_object.save_record.assert_called()

    def test_receive_multiple_records(self):
        record_list = [json.dumps(self.record_1), json.dumps(self.record_2)]
        self.test_request_video_record.connection.recv.return_value = str.encode('\n'.join(record_list))
        thread = self.test_object.ehandler_new_record(self.test_request_video_record)
        response = self.test_object.save_db_records_queue.get()
        self.assertEqual(self.record_1, response)
        response = self.test_object.save_db_records_queue.get()
        self.assertEqual(self.record_2, response)
        thread.join()

    def test_empty_string(self):
        self.test_request_video_record.connection.recv.return_value = b""
        thread = self.test_object.ehandler_new_record(self.test_request_video_record)
        thread.join()
        self.assertEqual(0, self.test_object.save_db_records_queue.qsize())

    def test_save_record_called(self):
        self.test_request_video_record.connection.recv.return_value = b""
        thread = self.test_object.ehandler_new_record(self.test_request_video_record)
        thread.join()
        self.test_object.save_record.assert_called()
    
    def test_save_or_update_camera_called(self):
        self.test_request_camera.connection.recv.return_value = b""
        thread = self.test_object.ehandler_new_record(self.test_request_camera)
        thread.join()
        self.test_object.save_or_update_camera.assert_called()
    
    def test_camera_record_added_to_queue(self):
        self.test_request_camera.connection.recv.return_value = str.encode(json.dumps(self.camera_record))
        thread = self.test_object.ehandler_new_record(self.test_request_camera)
        response = self.test_object.camera_records_queue.get()
        self.assertEqual(self.camera_record, response)
        thread.join()


class TestSaveRecord(TestCase):

    @classmethod
    def setUpClass(cls):            
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.time_1 = datetime.datetime.now(tz=timezone)
        cls.time_2 = datetime.datetime.now(tz=timezone) + datetime.timedelta(days=10)
        Camera.objects.create(camera_name='test', is_active=True)
        cls.camera_name = 'test'
        cls.record_1 = {'date_created': cls.time_1.isoformat(), 
                      'human_det':False,
                      'cat_det':False,
                      'car_det':False,
                      'chiken_det':False,
                      'camera_id':'test'}
        cls.record_2 = {'date_created':cls.time_2.isoformat(), 
                      'human_det':False,
                      'cat_det':False,
                      'car_det':False,
                      'chiken_det':False,
                      'camera_id':'test'}
        cls.corrupted_record = {'date_created': cls.time_1.isoformat(), 
                      'human_det':False,
                      'c111at_det':'abrakadabra',
                      'car_det':False,
                      'chiken_det':False,
                      'camera_id':'test'}

    @classmethod
    def tearDownClass(cls):
        records = ArchiveVideo.objects.all()
        for item in records:
            item.delete()

    @patch('camera_conn.connect_to_db')
    def test_connect_to_db_called(self, connect_to_db):
        connect_to_db.return_value = (None, None)
        thread = self.test_object.save_record()
        thread.join()
        connect_to_db.assert_called_once()

    def test_record_saved(self):
        records = ArchiveVideo.objects.all()
        for item in records:
            item.delete()

        self.test_object.save_db_records_queue.put(self.record_1)
        thread = self.test_object.save_record()
        thread.join()
        records = ArchiveVideo.objects.all()
        self.assertEqual(len(records), 1)
        self.assertEqual(self.time_1, records[0].date_created)
        self.assertEqual(self.camera_name, records[0].camera.camera_name)

    def test_corrupted_record_fail(self):
        records = ArchiveVideo.objects.all()
        for item in records:
            item.delete()

        self.test_object.save_db_records_queue.put(self.corrupted_record)
        thread = self.test_object.save_record()
        thread.join()
        records = ArchiveVideo.objects.all()
        self.assertEqual(len(records), 0)

    def test_multiple_records_saved(self):
        records = ArchiveVideo.objects.all()
        for item in records:
            item.delete()

        self.test_object.save_db_records_queue.put(self.record_1)
        self.test_object.save_db_records_queue.put(self.record_2)
        thread = self.test_object.save_record()
        thread.join()
        records = ArchiveVideo.objects.all()
        self.assertEqual(len(records), 2)

    def test_multiple_corrupted_records_fail(self):
        records = ArchiveVideo.objects.all()
        for item in records:
           item.delete()

        self.test_object.save_db_records_queue.put(self.corrupted_record)
        self.test_object.save_db_records_queue.put(self.record_1)
        self.test_object.save_db_records_queue.put(self.record_2)   
        thread = self.test_object.save_record()
        thread.join()
        records = ArchiveVideo.objects.all()
        self.assertEqual(len(records), 2)


class TestSaveOrUpdateCamera(TestCase):

    @classmethod
    def setUpClass(cls):            
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.test_camera_record_1 = {'camera_name':'test_camera_1'}
        cls.test_camera_record_2 = {'camera_name':'test_camera_2'}
    
    @classmethod
    def tearDownClass(cls):
        thread = cls.test_object.save_or_update_camera()
        thread.join()

    @patch('camera_conn.connect_to_db')
    def test_db_connect_called(self, connect_to_db):
        connect_to_db.return_value = None, None
        thread = self.test_object.save_or_update_camera()
        thread.join()
        connect_to_db.assert_called_once()

    def test_save_new_camera(self):
        self.test_object.camera_records_queue.put(self.test_camera_record_1)
        thread = self.test_object.save_or_update_camera()
        thread.join()
        records = Camera.objects.all()
        self.assertEqual(len(records), 1)

    def test_update_camera(self):
        self.test_object.camera_records_queue.put(self.test_camera_record_1)
        thread = self.test_object.save_or_update_camera()
        thread.join()
        self.test_object.camera_records_queue.put(self.test_camera_record_1)
        thread = self.test_object.save_or_update_camera()
        thread.join()
        record = Camera.objects.all()
        self.assertEqual(len(record), 1)
        self.assertTrue(record[0].is_active)

    def test_nonactive_camera_no_update(self):
        self.test_object.camera_records_queue.put(self.test_camera_record_1)
        self.test_object.camera_records_queue.put(self.test_camera_record_2)
        thread = self.test_object.save_or_update_camera()
        thread.join()
        self.test_object.camera_records_queue.put(self.test_camera_record_1)
        thread = self.test_object.save_or_update_camera()
        thread.join()
        record = Camera.objects.filter(is_active=True)
        self.assertEqual(1, len(record))

    def test_multiple_cameras_update(self):
        self.test_object.camera_records_queue.put(self.test_camera_record_1)
        self.test_object.camera_records_queue.put(self.test_camera_record_2)
        thread = self.test_object.save_or_update_camera()
        thread.join()
        records = Camera.objects.all()
        self.assertEqual(2, len(records))


class TestHandlerVideoResponse(TestCase):

    @classmethod
    def setUpClass(cls):  
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.request = ServerRequest(request_type='video_response',
                                    video_name='25-01-2021T14:29:18',
                                    video_size=125000)
        cls.video_name = '25-01-2021T14:29:18'
        cls.address = '127.0.0.1'
        cls.video_path = str(base_dir) +'/djbackend/mediafiles/25-01-2021T14:29:18.mp4'
    
    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.video_path):
            os.remove(cls.video_path)
    
    def test_video_received(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.recv.return_value = bytes(125000)
            self.request.connection = mock_socket
            self.test_object.ehandler_video_response(self.request)
            response = self.test_object.video_response_queue.get()
            self.assertEqual('success', response.request_result)
            self.assertEqual(self.video_name, response.video_name)
            self.assertTrue(os.path.exists(self.video_path))

    def test_failed_to_receive_video(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.recv.return_value = bytes(2)
            self.request.connection = mock_socket
            self.test_object.ehandler_video_response(self.request)
            response = self.test_object.video_response_queue.get()
            self.assertEqual('failure', response.request_result)
            self.assertEqual(self.video_name, response.video_name)

    def test_no_such_video(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.recv.return_value = None
            request = ServerRequest(request_type='video_response',
                                    video_name='25-01-2021T14:29:18',
                                    video_size=0,
                                    connection=mock_socket)            
            self.test_object.ehandler_video_response(request)
            response = self.test_object.video_response_queue.get()
            self.assertEqual('failure', response.request_result)
            self.assertEqual(self.video_name, response.video_name)


class TestHandlerUserAproveResponse(TestCase):

    @classmethod
    def setUpClass(cls):  
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        mock_socket = Mock()
        cls.request_accepted = ServerRequest(request_type='user_prove_response',
                                             request_result='aproved',
                                             username='username_1',
                                             connection=mock_socket)
        cls.request_denied = ServerRequest(request_type='user_prove_response',
                                             request_result='denied',
                                             username='username_2',
                                             connection=mock_socket)
        cls.pk_accepted = User.objects.create_user(username='username_1',
                         email='1@mail.ru',
                         password='123',
                         is_active = False,
                         admin_checked = False).pk
        cls.pk_denied = User.objects.create_user(username='username_2',
                         email='2@mail.ru',
                         password='123',
                         is_active = False,
                         admin_checked = False).pk
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    @patch('camera_conn.connect_to_db')
    def test_connect_to_db_called(self, connect_to_db):        
        connect_to_db.return_value = (None, None)
        thread = self.test_object.ehandler_user_aprove_response(self.request_accepted)
        thread.join()
        connect_to_db.assert_called_once()

    def test_accept_user(self):
        thread = self.test_object.ehandler_user_aprove_response(self.request_accepted)
        thread.join()
        user = User.objects.get(pk=self.pk_accepted)
        self.assertTrue(user.is_active)
        self.assertTrue(user.admin_checked)

    def test_deny_user(self):
        thread = self.test_object.ehandler_user_aprove_response(self.request_denied)
        thread.join()
        user = User.objects.get(pk=self.pk_denied)
        self.assertFalse(user.is_active)
        self.assertTrue(user.admin_checked)


class TestHandlerUserAproveRequest(TestCase):

    @classmethod
    def setUpClass(cls):  
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.request = ServerRequest(request_type='aprove_user_request',
                                    username='username',
                                    connection=Mock())
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_push_signal_to_queue(self):
        self.test_object.ihandler_aprove_user_request(self.request)
        response = self.test_object.signal_queue.get()
        self.assertEqual(self.request, response)


class TestHandlerVideoRequest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.request = ServerRequest(request_type='video_request', connection=Mock())
        cls.test_object.video_manager = Mock()

    @classmethod
    def tearDownClass(cls):
        pass

    def test_push_video_request_to_queue(self):
        self.test_object.ihandler_video_request(self.request)
        response = self.test_object.video_requesters_queue.get()
        self.assertEqual(self.request, response)

    def test_video_manager_called(self):
        self.test_object.ihandler_video_request(self.request)
        response = self.test_object.video_requesters_queue.get()
        self.test_object.video_manager.assert_called()


class TestVideoManager(TestCase):

    @classmethod
    def setUpClass(cls):  
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.request_1 = ServerRequest(request_type='video',
                                      video_name='20-01-2023T14:23:41',
                                      connection=Mock())
        cls.request_1_1 = ServerRequest(request_type='video',
                                      video_name='20-01-2023T14:23:41',
                                      connection=Mock())
        cls.request_2 = ServerRequest(request_type='video',
                                      video_name='10-01-2023T14:23:41',
                                      connection=Mock())
        cls.response_success = ServerRequest(request_type='video',
                                            request_result='success',
                                            video_name='20-01-2023T14:23:41')
        cls.response_success_2 = ServerRequest(request_type='video',
                                            request_result='success',
                                            video_name='10-01-2023T14:23:41')
        cls.response_failure = ServerRequest(request_type='video',
                                            request_result='failure',
                                            video_name='20-01-2023T14:23:41')
    
    @classmethod
    def tearDownClass(cls):
        pass

    def tearDown(self):
        self.test_object.flush_signal_queue()

    def test_successfully_request_video(self):
        self.test_object.video_requesters_queue.put(self.request_1)
        self.test_object.video_response_queue.put(self.response_success)
        thread = self.test_object.video_manager()
        thread.join()
        msg = 'success'
        self.request_1.connection.send.assert_called_with(msg.encode())

    def test_multiple_same_video_requests(self):
        self.test_object.video_requesters_queue.put(self.request_1)
        self.test_object.video_requesters_queue.put(self.request_1_1)
        self.test_object.video_response_queue.put(self.response_success)
        thread = self.test_object.video_manager()
        thread.join()
        signals = []
        while self.test_object.signal_queue.qsize() > 0:
            signal = self.test_object.signal_queue.get()
            signals.append(signal)
        self.assertEqual(1, len(signals))
        msg = 'success'
        self.request_1.connection.send.assert_called_with(msg.encode())
        self.request_1_1.connection.send.assert_called_with(msg.encode())

    def test_failure(self):
        self.test_object.video_requesters_queue.put(self.request_1)
        self.test_object.video_response_queue.put(self.response_failure)
        thread = self.test_object.video_manager()
        thread.join()
        msg = 'failure'
        self.request_1.connection.send.assert_called_with(msg.encode())

    def test_request_live_time(self):
        self.test_object.video_request_timeout = 1
        self.test_object.video_requesters_queue.put(self.request_1)
        thread = self.test_object.video_manager()
        thread.join()
        msg = 'failure'
        self.request_1.connection.send.assert_called_with(msg.encode())

    def test_multiple_video_requests(self):
        self.test_object.video_requesters_queue.put(self.request_1)
        self.test_object.video_requesters_queue.put(self.request_2)
        self.test_object.video_response_queue.put(self.response_success)
        self.test_object.video_response_queue.put(self.response_success_2)
        thread = self.test_object.video_manager()
        thread.join()
        msg = 'success'
        self.request_1.connection.send.assert_called_with(msg.encode())
        self.request_2.connection.send.assert_called_with(msg.encode())


class TestCheckConnection(TestCase):

    @classmethod
    def setUpClass(cls):  
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.log = Mock()
        cls.mock_socket = Mock()
        cls.signal = 'Restart'
        cls.mock_socket.recv= b""
        cls.result = ServerRequest(request_type=cls.signal)
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_break_connection(self):        
        thread = self.test_object.check_connection(self.log, self.mock_socket)
        thread.join()
        self.log.warning.assert_called_with('Connection lost')

    def test_push_signal(self):
        thread = self.test_object.check_connection(self.log, self.mock_socket, self.signal)
        thread.join()
        test_signal = self.test_object.signal_queue.get()
        self.assertEqual(self.result.request_type, test_signal.request_type)


class TestHandlerStreamSource(TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.request = ServerRequest(request_type='stream',
                                    camera_name='test')
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_put_new_source_to_queue(self):
        self.test_object.ehandler_stream_source(self.request)
        response = self.test_object.external_stream_responses.get()
        self.assertEqual(self.request, response)


class TestHandlerStreamRequest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.test_object.videostream_manager = Mock()
        cls.request = ServerRequest(request_type='stream',
                                    camera_name='test')
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_put_new_request_to_queue(self):
        self.test_object.ihandler_stream_request(self.request)
        response = self.test_object.internal_stream_requests.get()
        self.assertEqual(self.request, response)
    
    def test_videostream_manager_called(self):
        self.test_object.ihandler_stream_request(self.request)
        self.test_object.videostream_manager.assert_called()


class TestVideoStreamManager(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.camera_name = 'test_cam'
        cls.test_object.stream_channels = {cls.camera_name:StreamChannel(cls.camera_name)}
        cls.request = ServerRequest(request_type='stream',
                                    camera_name=cls.camera_name)
        cls.response = ServerRequest(request_type='stream',
                                    camera_name=cls.camera_name)
        cls.test_object.stream_channels[cls.camera_name].run_thread = Mock()
        cls.test_object.stream_channels[cls.camera_name].kill_thread = Mock()

    @classmethod
    def tearDownClass(cls):
        pass

    def tearDown(self):
        self.test_object.stream_channels[self.camera_name].kill_thread.reset_mock()
        self.test_object.stream_channels[self.camera_name].run_thread.reset_mock()
        self.test_object.stream_channels[self.camera_name].void_consumers()

    def test_put_new_consumer_to_proper_stream_channel(self):
        self.test_object.internal_stream_requests.put(self.request)
        thread = self.test_object.videostream_manager()
        thread.join()
        response = self.test_object.stream_channels[self.camera_name].consumer_queue.get()
        self.assertEqual(response, self.request)
        self.assertEqual(self.test_object.stream_channels[self.camera_name].consumer_number(),1)

    def test_put_new_source_to_proper_stream_channel(self):
        self.test_object.external_stream_responses.put(self.response)
        thread = self.test_object.videostream_manager()
        self.test_object.stream_channels[self.camera_name].wait_source_connection()
        thread.join()
        response = self.test_object.stream_channels[self.camera_name].stream_source        
        self.assertEqual(response, self.response)
        
    def test_start_thread_if_no_consumers(self):
        self.test_object.stream_channels[self.camera_name].void_consumers()
        self.test_object.internal_stream_requests.put(self.request)
        thread = self.test_object.videostream_manager()
        thread.join()
        self.test_object.stream_channels[self.camera_name].kill_thread.assert_called()
        self.test_object.stream_channels[self.camera_name].run_thread.assert_called()

    def test_not_starting_thread_if_any_consumers(self):        
        self.test_object.internal_stream_requests.put(self.request)
        self.test_object.stream_channels[self.camera_name].add_consumer()
        thread = self.test_object.videostream_manager()
        thread.join()
        self.test_object.stream_channels[self.camera_name].kill_thread.assert_not_called()
        self.test_object.stream_channels[self.camera_name].run_thread.assert_not_called()


class TestStreamChannel(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.camera_name = 'test'
        cls.test_object = StreamChannel(cls.camera_name)
        cls.test_object.source_connected()
        cls.stream_source = ServerRequest(request_type='stream',
                                          camera_name=cls.camera_name,
                                          connection=Mock())
        cls.stream_source.connection.recv.return_value = b"100"
        cls.consumer_1 = ServerRequest(request_type='stream',
                                     camera_name=cls.camera_name,
                                     connection=Mock())
        cls.consumer_2 = ServerRequest(request_type='stream',
                                     camera_name=cls.camera_name,
                                     connection=Mock())
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def setUp(self):
        self.test_object.source_connected()
        self.test_object.stream_source = self.stream_source
        self.test_object.consumer_queue.put(self.consumer_1)
        self.test_object.add_consumer()

    def test_send_data_to_consumer(self):
        self.test_object.run_thread()
        time.sleep(0.5)
        self.test_object.kill_thread()
        self.consumer_1.connection.send.assert_called_with(b'100')

    def test_send_data_to_multiple_consumers(self):
        self.test_object.consumer_queue.put(self.consumer_2)
        self.test_object.add_consumer()
        self.test_object.run_thread()
        time.sleep(0.5)
        self.test_object.kill_thread()
        self.consumer_1.connection.send.assert_called_with(b'100')
        self.consumer_2.connection.send.assert_called_with(b'100')

    def test_close_connection_if_no_source(self):
        self.test_object.stream_source = None
        self.test_object.source_connection_timeout = 1
        self.test_object.source_disconnected()
        self.test_object.run_thread()
        time.sleep(1.2)
        self.consumer_1.connection.close.assert_called()
    
    def test_remove_consumer_if_disconnected(self):
        self.consumer_1.connection.send.side_effect = OSError
        self.test_object.run_thread()
        time.sleep(0.5)
        self.consumer_1.connection.close.assert_called()
        self.assertEqual(self.test_object.consumer_number(), 0)