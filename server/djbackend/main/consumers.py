import socket
import asyncio
import queue
import os
import json
import struct
from asgiref.sync import async_to_sync
from .utils import check_named_thread, recv_package
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
import logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(name)s | %(levelname)s | %(asctime)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                    )

consumers = {'1':queue.Queue(), '2':queue.Queue(), '3':queue.Queue(), '4':queue.Queue()}

@check_named_thread
def camera_source(camera_name):
    payload_size = struct.calcsize("Q")
    data = b"" 
    consumer_list = []
    camera_name = str(camera_name)

    isock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    isock.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))    
    msg = {'request_type':'stream_request', 'camera_name':camera_name}
    isock.send(json.dumps(msg).encode())

    while True:
        while consumers[camera_name].qsize() > 0:                
            consumer_list.append(consumers[camera_name].get())    
            logging.debug('get consumer. %s', consumer_list[0])

        isock, frame_data, data, connection_failure = recv_package(
                                                                isock,
                                                                data, 
                                                                payload_size,
                                                                )
        if connection_failure:
            break
        logging.debug('Frame received') 
        if consumer_list:
            logging.debug('consumer list get')
            for consumer in consumer_list:
                if consumer[0].qsize() == 0 and consumer[1].qsize() == 0:
                    consumer[0].put(frame_data)
                elif consumer[1].qsize() > 0:
                    consumer_list.remove(consumer)
                    logging.debug('Consumer removed')
        else:
            logging.debug('NO consumers')
            break
    logging.debug('CLOSE SOCKET')
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
            try:
                frame = self.frame.get(timeout=1)
            except:
                self.connected = False
            else:
                self.sync_send(frame.decode('utf-8'))

    async def connect(self):
        self.camera_name = self.scope["url_route"]["kwargs"]["camera_name"]
        camera_source(self.camera_name)
        consumers[str(self.camera_name)].put((self.frame, self.signal))
        self.connected = True
        await self.accept()        
        self.loop.run_in_executor(None, self.videostream)
       
    async def disconnect(self, close_code):
        self.connected = False
        self.signal.put('remove consumer')
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
