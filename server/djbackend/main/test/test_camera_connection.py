import socket
import json
import threading
import sys
import datetime
import os
import pytz
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
        cls.reply = 'accepted'
        for item in cls.test_object.external_handlers.keys():
            cls.test_object.external_handlers[item] = Mock(name=item)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_signal_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
            request = {'request_type':'signal'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()

    def test_stream_source_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
            request = {'request_type':'stream_source'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()

    def test_new_record_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
            request = {'request_type':'new_record'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()

    def test_video_response_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
            request = {'request_type':'video_response'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()
    
    def test_user_aprove_handler(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
            request = {'request_type':'user_aprove_response'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_external_server(mock_socket)
            thread.join()
            mock_socket.send.assert_called_with(self.reply.encode())
        self.test_object.external_handlers[request['request_type']].assert_called_once()

    def test_wrong_request_type(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
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
        for item in cls.test_object.internal_handlers.keys():
            cls.test_object.internal_handlers[item] = Mock(name=item)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_aprove_user_request_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
            request = {'request_type':'aprove_user_request'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_internal_server(mock_socket)
            thread.join()
        self.test_object.internal_handlers[request['request_type']].assert_called_once()

    def test_video_request_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
            request = {'request_type':'video_request'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_internal_server(mock_socket)
            thread.join()
        self.test_object.internal_handlers[request['request_type']].assert_called_once()

    def test_steam_request_handler_called(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
            request = {'request_type':'stream_request'}
            mock_socket.recv.return_value = json.dumps(request).encode()
            thread = self.test_object.run_internal_server(mock_socket)
            thread.join()
        self.test_object.internal_handlers[request['request_type']].assert_called_once()

    def test_wrong_request_type(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.accept.return_value = (mock_socket, self.adress)
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
        th_runing = False
        for th in threading.enumerate():
            if th.name == 'ehandler_signal':
                th_runing = True
                break
        self.assertTrue(th_runing)
        self.test_object.signal_queue.put(ServerRequest(request_type='restart'))
        thread.join()      
        th_runing = False
        for th in threading.enumerate():
            if th.name == 'ehandler_signal':
                th_runing = True
                break
        self.assertFalse(th_runing)


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
        cls.corrupted_record = {'date_created': cls.time_1.isoformat(), 
                      'human_det':False,
                      'c111at_det':'abrakadabra',
                      'car_det':False,
                      'chiken_det':False}
        
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

    def test_db_connect_called(self):
        pass

    def test_save_new_camera(self):
        pass

    def test_update_camera(self):
        pass

    def test_nonactive_camera_no_update(self):
        pass
    
    def test_multiple_cameras_update(self):
        pass
    
    def test_corrupted_record(self):
        pass


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
            self.test_object.ehandler_video_response(self.request, mock_socket, self.address)
            response = self.test_object.video_response_queue.get()
            self.assertEqual('success', response.request_result)
            self.assertEqual(self.video_name, response.video_name)
            self.assertTrue(os.path.exists(self.video_path))

    def test_failed_to_receive_video(self):
        with patch('socket.socket') as mock_socket:
            mock_socket.recv.return_value = bytes(2)
            self.test_object.ehandler_video_response(self.request, mock_socket, self.address)
            response = self.test_object.video_response_queue.get()
            self.assertEqual('failure', response.request_result)
            self.assertEqual(self.video_name, response.video_name)

    def test_no_such_video(self):
        with patch('socket.socket') as mock_socket:
            request = ServerRequest(request_type='video_response',
                                    video_name='25-01-2021T14:29:18',
                                    video_size=0)
            mock_socket.recv.return_value = None
            self.test_object.ehandler_video_response(request, mock_socket, self.address)
            response = self.test_object.video_response_queue.get()
            self.assertEqual('failure', response.request_result)
            self.assertEqual(self.video_name, response.video_name)


class TestHandlerUserAproveResponse(TestCase):

    @classmethod
    def setUpClass(cls):  
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.address = '127.0.0.1'
        cls.request_accepted = ServerRequest(request_type='user_prove_response',
                                             request_result='aproved',
                                             username='username_1')
        cls.request_denied = ServerRequest(request_type='user_prove_response',
                                             request_result='denied',
                                             username='username_2')
        cls.mock_socket = Mock()
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
        self.test_object.ehandler_user_aprove_response(self.request_accepted, self.mock_socket, self.address)
        response = self.test_object.test_queue.get()
        connect_to_db.assert_called_once()

    def test_accept_user(self):
        self.test_object.ehandler_user_aprove_response(self.request_accepted, self.mock_socket, self.address)
        response = self.test_object.test_queue.get()
        user = User.objects.get(pk=self.pk_accepted)
        self.assertTrue(user.is_active)
        self.assertTrue(user.admin_checked)

    def test_deny_user(self):
        self.test_object.ehandler_user_aprove_response(self.request_denied, self.mock_socket, self.address)
        response = self.test_object.test_queue.get()
        user = User.objects.get(pk=self.pk_denied)
        self.assertFalse(user.is_active)
        self.assertTrue(user.admin_checked)


class TestHandlerUserAproveRequest(TestCase):

    @classmethod
    def setUpClass(cls):  
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        cls.address = '127.0.0.1'
        cls.request = ServerRequest(request_type='aprove_user_request',
                                    username='username')
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_push_signal_to_queue(self):
        self.test_object.ihandler_aprove_user_request(self.request, self.mock_socket, self.address)
        response = self.test_object.signal_queue.get()
        self.assertEqual(self.request, response)


class TestHandlerStreamRequest(TestCase):

    @classmethod
    def setUpClass(cls):  
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        cls.address = '127.0.0.1'
        cls.request = ServerRequest(request_type='stream_request')
        cls.test_object.restream_video = Mock()
    
    @classmethod
    def tearDownClass(cls):
        pass
    
    def test_push_stream_request_to_queue(self):
        self.test_object.ihandler_stream_request(self.request, self.mock_socket, self.address)
        response = self.test_object.stream_requesters_queue.get()
        self.assertEqual(self.sock.connection, response.connection)

    def test_restream_video_called(self):
        self.test_object.ihandler_stream_request(self.request, self.mock_socket, self.address)
        response = self.test_object.stream_requesters_queue.get()
        self.test_object.restream_video.assert_called()


class TestHandlerVideoRequest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.mock_socket = Mock()
        cls.address = '127.0.0.1'
        cls.request = ServerRequest(request_type='video_request')
        cls.test_object.video_manager = Mock()

    @classmethod
    def tearDownClass(cls):
        pass

    def test_push_video_request_to_queue(self):
        self.test_object.ihandler_video_request(self.request, self.mock_socket, self.address)
        response = self.test_object.video_requesters_queue.get()
        self.assertEqual(self.sock.request, response.request)

    def test_video_manager_called(self):
        self.test_object.ihandler_video_request(self.request, self.mock_socket, self.address)
        response = self.test_object.video_requesters_queue.get()
        self.test_object.video_manager.assert_called()


class TestRestreamVideo(TestCase):

    @classmethod
    def setUp(cls):  
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.test_object.stream_q_timeout = 0.1
        cls.mock_socket = Mock()
        cls.address = '127.0.0.1'

    def test_push_signal_to_start_stream(self):        
        self.test_object.restream_video()
        response = self.test_object.signal_queue.get()
        self.assertEqual('stream', response.request_type)

    @patch('camera_conn.recv_package')
    def test_get_stream_source_connection(self, recv_package):
        recv_package.return_value = None, None, None, True
        self.test_object.stream_queue.put(SocketConn(self.mock_socket, self.address))
        self.test_object.restream_video()
        thread_ended = self.test_object.test_queue.get()
        response = self.test_object.signal_queue.get()
        response = self.test_object.signal_queue.get()
        recv_package.assert_called_once()
        self.assertEqual('restart stream', response.request_type)        

    def test_failed_stream_source_connection(self):
        self.test_object.restream_video()
        thread_ended = self.test_object.test_queue.get()
        response = self.test_object.signal_queue.get()
        self.assertEqual('stream', response.request_type)
        response_fail = self.test_object.signal_queue.get()
        self.assertEqual('restart stream', response_fail.request_type)
        
    @patch('camera_conn.recv_package')
    def test_empty_requester_list(self, recv_package):
        self.test_object.stream_queue.put(SocketConn(self.mock_socket, self.address))
        recv_package.return_value = self.mock_socket, bytes(10), bytes(1), False
        self.test_object.restream_video()
        thread_ended = self.test_object.test_queue.get()
        response = self.test_object.signal_queue.get()
        self.assertEqual('stream', response.request_type)
        response = self.test_object.signal_queue.get()
        recv_package.assert_called_once()
        self.assertEqual('stop', response.request_type)

    @patch('camera_conn.recv_package')
    def test_one_requester(self, recv_package):
        self.test_object.stream_queue.put(SocketConn(self.mock_socket, self.address))
        recv_package.return_value = self.mock_socket, bytes(10), bytes(1), False
        requester_1 = SocketConn(Mock(name='requester_1'), self.address)
        self.test_object.stream_requesters_queue.put(requester_1)
        self.test_object.restream_video()
        thread_ended = self.test_object.test_queue.get()
        response = self.test_object.signal_queue.get()
        self.assertEqual('stream', response.request_type)
        recv_package.assert_called_once()
        requester_1.connection.send.assert_called_once()

    @patch('camera_conn.recv_package')
    def test_multiple_requesters(self, recv_package):
        self.test_object.stream_queue.put(SocketConn(self.mock_socket, self.address))
        recv_package.return_value = self.mock_socket, bytes(10), bytes(1), False
        requester_1 = SocketConn(Mock(name='requester_1'), self.address)
        requester_2 = SocketConn(Mock(name='requester_2'), self.address)
        self.test_object.stream_requesters_queue.put(requester_1)
        self.test_object.stream_requesters_queue.put(requester_2)
        self.test_object.restream_video()
        thread_ended = self.test_object.test_queue.get()
        response = self.test_object.signal_queue.get()
        self.assertEqual('stream', response.request_type)
        recv_package.assert_called_once()
        requester_1.connection.send.assert_called_once()
        requester_2.connection.send.assert_called_once()


class TestVideoManager(TestCase):

    @classmethod
    def setUp(cls):  
        cls.test_object = EchoServer('127.0.0.1', 20900, '127.0.0.1', 10900)
        cls.test_object.DEBUG = True
        cls.address = '127.0.0.1'
    
    def test_successfully_request_video(self):
        mock_socket = Mock()
        self.test_object.video_requesters_queue.put(SocketConn(mock_socket, 
                                                               self.address, 
                                                               request=ServerRequest(request_type='video',
                                                                                     video_name='20-01-2023T14:23:41')))
        self.test_object.video_response_queue.put(ServerRequest(request_type='video',
                                                                request_result='success',
                                                                video_name='20-01-2023T14:23:41'))
        self.test_object.video_manager()
        msg = 'success'
        response = self.test_object.test_queue.get()
        mock_socket.send.assert_called_once_with(msg.encode())

    def test_multiple_same_video_requests(self):
        mock_socket_1 = Mock()
        mock_socket_2 = Mock()
        self.test_object.video_requesters_queue.put(SocketConn(mock_socket_1, 
                                                               self.address, 
                                                               request=ServerRequest(request_type='video',
                                                                                     video_name='20-01-2023T14:23:41')))
        self.test_object.video_requesters_queue.put(SocketConn(mock_socket_2, 
                                                               self.address, 
                                                               request=ServerRequest(request_type='video',
                                                                                     video_name='20-01-2023T14:23:41')))
        self.test_object.video_response_queue.put(ServerRequest(request_type='video',
                                                                request_result='success',
                                                                video_name='20-01-2023T14:23:41'))
        self.test_object.video_manager()
        response = self.test_object.test_queue.get()
        signals = []
        while self.test_object.signal_queue.qsize() > 0:
            signal = self.test_object.signal_queue.get()
            signals.append(signal)
        self.assertEqual(1, len(signals))
        msg = 'success'
        mock_socket_1.send.assert_called_once_with(msg.encode())
        mock_socket_2.send.assert_called_once_with(msg.encode())
    
    def test_failure(self):
        mock_socket = Mock()
        self.test_object.video_requesters_queue.put(SocketConn(mock_socket, 
                                                               self.address, 
                                                               request=ServerRequest(request_type='video',
                                                                                     video_name='20-01-2023T14:23:41')))
        self.test_object.video_response_queue.put(ServerRequest(request_type='video',
                                                                request_result='failure',
                                                                video_name='20-01-2023T14:23:41'))
        self.test_object.video_manager()
        response = self.test_object.test_queue.get()
        msg = 'failure'
        mock_socket.send.assert_called_once_with(msg.encode())

    def test_request_live_time(self):
        self.test_object.video_request_timeout = 1
        mock_socket = Mock()
        self.test_object.video_requesters_queue.put(SocketConn(mock_socket, 
                                                               self.address, 
                                                               request=ServerRequest(request_type='video',
                                                                                     video_name='20-01-2023T14:23:41')))
        self.test_object.video_manager()
        response = self.test_object.test_queue.get()
        msg = 'failure'
        mock_socket.send.assert_called_once_with(msg.encode())

    def test_multiple_video_requests(self):
        mock_socket_1 = Mock()
        mock_socket_2 = Mock()
        self.test_object.video_requesters_queue.put(SocketConn(mock_socket_1, 
                                                               self.address, 
                                                               request=ServerRequest(request_type='video',
                                                                                     video_name='20-01-2023T14:23:41')))
        self.test_object.video_requesters_queue.put(SocketConn(mock_socket_2, 
                                                               self.address, 
                                                               request=ServerRequest(request_type='video',
                                                                                     video_name='01-01-2023T14:23:41')))
        self.test_object.video_response_queue.put(ServerRequest(request_type='video',
                                                                request_result='success',
                                                                video_name='20-01-2023T14:23:41'))
        self.test_object.video_response_queue.put(ServerRequest(request_type='video',
                                                                request_result='success',
                                                                video_name='01-01-2023T14:23:41'))
        self.test_object.video_manager()
        response = self.test_object.test_queue.get()
        msg = 'success'
        mock_socket_1.send.assert_called_once_with(msg.encode())
        mock_socket_2.send.assert_called_once_with(msg.encode())


class TestCheckConnection(TestCase):

    @classmethod
    def setUp(cls):  
        cls.test_object = EchoServer('127.0.0.1', 20900, '127.0.0.1', 10900)
        cls.test_object.DEBUG = True
        cls.address = '127.0.0.1'
        cls.log = Mock()
        cls.mock_socket = Mock()
        cls.signal = 'Restart'
        cls.mock_socket.recv= b""
        cls.result = ServerRequest(request_type=cls.signal)
    
    def test_break_connection(self):        
        self.test_object.check_connection(self.log, self.mock_socket)
        response = self.test_object.test_queue.get()
        self.mock_socket.close.assert_called_once()

    def test_push_signal(self):
        self.test_object.check_connection(self.log, self.mock_socket, self.signal)
        response = self.test_object.test_queue.get()
        test_signal = self.test_object.signal_queue.get()
        self.mock_socket.close.assert_called_once()
        self.assertEqual(self.result.request_type, test_signal.request_type)








class TestHandlerStreamSource(TestCase):

    @classmethod
    def setUp(cls):       
        cls.test_object = EchoServer(test_adress, test_port_1, test_adress, test_port_2)
        cls.test_object.DEBUG = True
        cls.connection = Mock()
        cls.address = '127.0.0.1'
    
    def test_stream_source_queue(self):
        self.test_object.ehandler_stream_source({}, self.connection, self.address)
        response = self.test_object.stream_queue.get()
        self.assertEqual(response.connection, self.sock.connection)
