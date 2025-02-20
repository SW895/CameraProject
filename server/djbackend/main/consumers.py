import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from prometheus_client import Summary
# from .utils import new_thread

bytes_sended = Summary(
    'djbackend_websocket_bytes_sended',
    'Bytes sended through websocket',
)
import logging
from .utils import VideoStreamManager

class VideoStreamConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        self.manager = VideoStreamManager()
        self._disconnected = asyncio.Event()
        self.frame = asyncio.Queue(maxsize=1)
        self._videostream = None
        self.log = logging.getLogger('ZZZZ')
        super().__init__(*args, **kwargs)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['frame'],
        del state['_disconnected'],
        del state['_pause_stream'],
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.frame = asyncio.Queue(maxsize=1)
        self._disconnected = asyncio.Event()

    def is_disconnected(self):
        return self._disconnected.is_set()

    def end_consumer(self):
        self._disconnected.set()

    def stop_videostream(self):
        self._videostream.cancel()

    async def get_frame(self):
        try:
            frame = await asyncio.wait_for(self.frame.get(), timeout=5)
        except asyncio.TimeoutError():
            #self.pause_stream()
            return None
        else:
            return frame

    async def videostream(self):
        while True:
            try:
                frame = await self.get_frame()
            except asyncio.CancelledError:
                break
            if frame:
                try:
                    await self.send(frame.decode('utf-8'))
                    bytes_sended.observe(len(frame.decode('utf-8')))
                except Exception:
                    break

    async def connect(self):
        self.log.debug('CONSUMER_CONNECTED')
        self.camera_name = self.scope["url_route"]["kwargs"]["camera_name"]
        self.manager.run_manager()
        await self.manager.consumer_queue.put(self)
        self.log.debug('PUT SELF TO MANAGER QUEUE')
        loop = asyncio.get_event_loop()
        self._videostream = loop.create_task(self.videostream())
        await self.accept()

    async def disconnect(self, close_code):
        self.stop_videostream()
        self.end_consumer()
        await self.close()

    async def receive(self, text_data):
        request = json.loads(text_data)
        signal = request['signal']
        if signal == 'pause':
            self.stop_videostream()
        elif signal == 'play' and self.is_paused():
            loop = asyncio.get_event_loop()
            self._videostream = loop.create_task(self.videostream())
