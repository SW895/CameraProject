import queue
import json
import threading
from channels.generic.websocket import WebsocketConsumer
from channels.exceptions import StopConsumer
from .utils import VideoStreamManager, new_thread


class VideoStreamConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        self._pause_stream = threading.Event()
        self._disconnected = threading.Event()
        self.frame = queue.Queue(maxsize=1)        
        super().__init__(*args, **kwargs)

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

    @new_thread
    def videostream(self):
        while not self.is_paused():
            try:
                frame = self.frame.get(timeout=10)
            except:
                self.pause_stream()
            else:
                try:
                    self.send(frame.decode('utf-8'))
                except:
                    self.pause_stream()

    @new_thread
    def connect(self):
        self.camera_name = self.scope["url_route"]["kwargs"]["camera_name"]
        if not(self.camera_name in manager.stream_sources) and manager.is_valid():
            manager.stream_sources_invalid()

        manager.consumer_queue.put(self)
        manager.wait_validation()
        self.videostream()
        self.accept()

    @new_thread
    def disconnect(self, close_code):
        self.pause_stream()
        self.end_consumer()    
        self.close()
        raise StopConsumer()
    
    @new_thread
    def receive(self, text_data):
        request = json.loads(text_data)
        signal = request['signal']
        if signal == 'pause':
            self.pause_stream()
        elif signal == 'play' and self.is_paused():
            self.play_stream()
            self.videostream()


manager = VideoStreamManager()
manager.run_manager()