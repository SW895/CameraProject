import queue
import json
import threading
from channels.generic.websocket import WebsocketConsumer
from .utils import new_thread


class VideoStreamConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        self.manager = kwargs['manager']
        self._pause_stream = threading.Event()
        self._disconnected = threading.Event()
        self.frame = queue.Queue(maxsize=1)
        super().__init__(*args, **kwargs)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['frame'],
        del state['_disconnected'],
        del state['_pause_stream'],
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.frame = queue.Queue(maxsize=1)
        self._pause_stream = threading.Event()
        self._disconnected = threading.Event()

    def is_disconnected(self):
        return self._disconnected.is_set()

    def end_consumer(self):
        self._disconnected.set()

    def pause_stream(self):
        self._pause_stream.set()

    def play_stream(self):
        self._pause_stream.clear()

    def is_paused(self):
        return self._pause_stream.is_set()

    def get_frame(self):
        try:
            frame = self.frame.get(timeout=5)
        except Exception:
            self.pause_stream()
            return None
        else:
            return frame

    @new_thread
    def videostream(self):
        while not self.is_paused():
            frame = self.get_frame()
            if frame:
                try:
                    self.send(frame.decode('utf-8'))
                except Exception:
                    self.pause_stream()

    @new_thread
    def connect(self):
        self.camera_name = self.scope["url_route"]["kwargs"]["camera_name"]
        self.manager.consumer_queue.put(self)
        self.videostream()
        self.accept()

    @new_thread
    def disconnect(self, close_code):
        self.pause_stream()
        self.end_consumer()
        self.close()

    @new_thread
    def receive(self, text_data):
        request = json.loads(text_data)
        signal = request['signal']
        if signal == 'pause':
            self.pause_stream()
        elif signal == 'play' and self.is_paused():
            self.play_stream()
            self.videostream()
