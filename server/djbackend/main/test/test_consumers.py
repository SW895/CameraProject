from django.test import SimpleTestCase
from unittest.mock import Mock, patch
from django.urls import path
from channels.routing import URLRouter
from channels.testing.websocket import WebsocketCommunicator
from ..consumers import VideoStreamConsumer


class TestVideoStream(SimpleTestCase):

    @patch('main.consumers.VideoStreamConsumer.get_frame')
    async def test_consumer(self, get_frame):
        manager = Mock()
        get_frame.return_value = b'frame'
        application = URLRouter([
            path("testws/stream/<str:camera_name>/",
                 VideoStreamConsumer.as_asgi(manager=manager))
        ])
        self.communicator = WebsocketCommunicator(
            application,
            '/testws/stream/test/'
        )
        connected, subprotocol = await self.communicator.connect()
        response = await self.communicator.receive_from()
        self.assertEqual(response, 'frame')
        manager.consumer_queue.put.assert_called_once()
        await self.communicator.disconnect()

    @patch('main.consumers.VideoStreamConsumer.get_frame')
    async def test_pause_stream(self, get_frame):
        manager = Mock()
        get_frame.return_value = b'frame'
        application = URLRouter([
            path("testws/stream/<str:camera_name>/",
                 VideoStreamConsumer.as_asgi(manager=manager))
        ])
        self.communicator = WebsocketCommunicator(
            application,
            '/testws/stream/test/'
        )
        connected, subprotocol = await self.communicator.connect()
        await self.communicator.send_json_to({"signal": "pause"})
        response = None
        try:
            response = await self.communicator.receive_from()
        except Exception:
            pass
        self.assertIsNone(response)
        manager.consumer_queue.put.assert_called_once()
        await self.communicator.disconnect()

    @patch('main.consumers.VideoStreamConsumer.get_frame')
    async def test_pause_and_play_stream(self, get_frame):
        manager = Mock()
        get_frame.return_value = b'frame'
        application = URLRouter([
            path("testws/stream/<str:camera_name>/",
                 VideoStreamConsumer.as_asgi(manager=manager))
        ])
        self.communicator = WebsocketCommunicator(
            application,
            '/testws/stream/test/'
        )
        connected, subprotocol = await self.communicator.connect()
        await self.communicator.send_json_to({"signal": "pause"})
        response = None
        try:
            response = await self.communicator.receive_from()
        except Exception:
            pass
        self.assertIsNone(response)
        await self.communicator.send_json_to({"signal": "play"})
        response = await self.communicator.receive_from()
        self.assertEqual(response, 'frame')
        manager.consumer_queue.put.assert_called_once()
        await self.communicator.disconnect()
