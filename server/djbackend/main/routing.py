from django.urls import path
from . import consumers
from .utils import VideoStreamManager

import asyncio

#loop = asyncio.get_running_loop()

import threading
import logging

for thread in threading.enumerate():
    logging.critical('ZZZZ :%s', thread)
#manager = VideoStreamManager()
#manager.log.info('AAAAAAAAAAA')
#manager.run_manager()
#loop.create_task(manager.run())

websocket_urlpatterns = [
    path('ws/stream/<str:camera_name>/', consumers.VideoStreamConsumer.as_asgi()),
]
