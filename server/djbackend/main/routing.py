from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/stream/<int:camera_name>/', consumers.VideoStreamConsumer.as_asgi()),
]