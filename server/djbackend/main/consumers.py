import socket
import asyncio
import queue
import os
import json
from asgiref.sync import async_to_sync
from .utils import check_thread
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer


consumer_queue = queue.Queue()

@check_thread
def camera_source():
    isock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    isock.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))
    consumer_list = []
    msg = {'request_type':'stream_request'}
    isock.send(json.dumps(msg).encode())
    while True:
        if consumer_queue.qsize() > 0:
            while consumer_queue.qsize() > 0:
                consumer_list.append(consumer_queue.get())        
        frame = isock.recv(1048576)
        if consumer_list:
            for consumer in consumer_list:
                if consumer[0].qsize() == 0 and consumer[1].qsize() == 0:
                        consumer[0].put(frame)
                elif consumer[1].qsize() > 0:
                    consumer_list.remove(consumer)
        else:
            break
    isock.close()


class VideoStreamConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):      
        self.connected = True
        self.loop = asyncio.get_running_loop()
        self.sync_send = async_to_sync(self.send)
        self.frame = queue.Queue(maxsize=1)
        self.signal = queue.Queue(maxsize=1)
        super().__init__(*args, **kwargs)        

    def videostream(self):
        while self.connected:
            frame = self.frame.get()
            self.sync_send(frame.decode('utf-8'))

    async def connect(self):
        camera_source()
        consumer_queue.put((self.frame, self.signal))
        self.connected = True
        await self.accept()        
        self.loop.run_in_executor(None, self.videostream)
       
    async def disconnect(self, close_code):
        self.connected = False
        self.signal.put('z')
        await self.close()
        raise StopConsumer()

    async def receive(self, text_data):
        request = json.loads(text_data)
        signal = request['signal']
        if signal == 'pause':
            self.connected = False
        elif signal == 'play' and self.connected == False:
            self.connected = True
            self.loop.run_in_executor(None, self.videostream)
