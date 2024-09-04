from django.test import TestCase
from ..utils import VideoStreamManager, VideoStreamSource
from ..models import Camera
from unittest.mock import Mock


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
        cls.valid_test_camera_pk = Camera.objects.create(
            camera_name=cls.valid_camera_name,
            is_active=True
        ).pk
        cls.invalid_test_camera_pk = Camera.objects.create(
            camera_name=cls.invalid_camera_name,
            is_active=False
        ).pk

    def test_correct_stream_source_validation(self):
        self.test_object.validate_stream_sources()
        self.assertTrue(
            self.valid_camera_name in self.test_object.stream_sources
        )
        self.assertFalse(
            self.invalid_camera_name in self.test_object.stream_sources
        )
