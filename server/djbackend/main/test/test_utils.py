from django.test import TestCase
from ..utils import VideoStreamManager, VideoStreamSource
from ..models import Camera
from unittest.mock import Mock, patch

class TestVideoStreamManagerStreamSource(TestCase):

    @classmethod
    def setUp(cls):
        cls.test_object = VideoStreamSource('test_camera')
        cls.test_consumer = Mock()

    def test_get_connection_called(self):
        self.test_object.get_connection = Mock(return_value=False)
        self.test_object.stream_source()
        self.test_object.get_connection.assert_called_once()

    def test_put_frame_to_queue(self):
        self.test_object.get_connection = Mock(return_value=True)
        self.test_object.add_consumer()
        self.assertEqual(1, self.test_object.consumer_number())
        self.test_consumer.frame.qsize.return_value = 0 
        self.test_object.consumer_queue.put(self.test_consumer)
        self.test_object.recv_package = Mock(return_value=(b'frame', b""))
        self.test_object.stream_source()
        self.test_object.wait_end_thread()
        self.test_consumer.frame.put.assert_called_once_with(b'frame')
        self.assertEqual(0, self.test_object.consumer_number())

    def test_remove_disconnected_consumer(self):
        self.test_object.get_connection = Mock(return_value=True)
        self.test_object.add_consumer()
        self.test_consumer.is_disconnected.return_value = True
        self.test_object.recv_package = Mock(return_value=(b'frame', b""))
        self.test_object.consumer_queue.put(self.test_consumer)
        self.assertEqual(1, self.test_object.consumer_number())
        self.test_object.stream_source()
        self.test_object.wait_end_thread()
        self.assertEqual(0, self.test_object.consumer_number())

    def test_disconnect_consumer_if_no_source(self):
        self.test_object.get_connection = Mock(return_value=False)
        self.test_object.add_consumer()
        self.test_object.consumer_queue.put(self.test_consumer)
        self.test_object.stream_source()
        self.test_object.wait_end_thread()
        self.test_consumer.disconnect.assert_called_once()


class TestVideoStreamManagerValidateStreamSource(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.test_object = VideoStreamManager()
        cls.valid_camera_name = 'test_camera_1'
        cls.invalid_camera_name = 'test_camera_2'
        cls.valid_test_camera_pk = Camera.objects.create(camera_name=cls.valid_camera_name, 
                                                          is_active=True).pk
        cls.invalid_test_camera_pk = Camera.objects.create(camera_name=cls.invalid_camera_name,
                                                            is_active=False).pk

    def test_correct_stream_source_validation(self):
        self.test_object.validate_stream_sources()
        self.assertTrue(self.valid_camera_name in self.test_object.stream_sources)
        self.assertFalse(self.invalid_camera_name in self.test_object.stream_sources)
      

"""
class TestVideoStreamManagerRunManager(TestCase):

    @classmethod
    def setUp(cls):
        cls.test_object = VideoStreamManager()
        cls.valid_camera_name = 'test_camera_1'
        test_stream_source = VideoStreamSource(cls.valid_camera_name)
        test_stream_source.kill_thread = Mock()
        test_stream_source.run_thread = Mock()
        cls.invalid_test_consumer = Mock()
        cls.invalid_test_consumer.camera_name = 'invalid_name'
        cls.test_object.stream_sources = {cls.valid_camera_name:test_stream_source}

    def test_call_validation_if_consumer_is_not_in_stream_sources(self):
        pass

    def test_kill_and_run_new_thread_if_no_consumers(self):
        pass

    def test_add_consumer_if_there_any_consumers(self):
        pass
    
"""