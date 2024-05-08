from django.urls import path
from . import consumers
from .utils import VideoStreamManager

manager = VideoStreamManager()
manager.run_manager()

websocket_urlpatterns = [
    path('ws/stream/<str:camera_name>/', consumers.VideoStreamConsumer.as_asgi(manager=manager)),
]


