from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/stream/<str:camera_name>/', consumers.VideoStreamConsumer.as_asgi()),
]