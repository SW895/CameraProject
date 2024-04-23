import socket
import asyncio
import queue
import os
import json
import struct
from asgiref.sync import async_to_sync
from .utils import check_named_thread, recv_package

from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.exceptions import StopConsumer
import logging
import time
import threading


from django.core.cache import cache

logging.basicConfig(level=logging.DEBUG,
                    format="%(name)s | %(levelname)s | %(asctime)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                    )

"""
consumers = {}
consumers_ready = queue.Queue(maxsize=1)


@check_named_thread
def init_cam_queues(name):
    global consumers, consumers_ready
    from .models import Camera
    camera_list = Camera.objects.filter(is_active=True)
    logging.critical('CREATE CONSUMERS DICT')
    for camera in camera_list:
        consumers[camera.camera_name] = queue.Queue()
        logging.critical('ADD CINSUMER:%s', camera.camera_name)
    consumers_ready.put('ready')

#consumers = {'1':queue.Queue(), '2':queue.Queue(), '3':queue.Queue(), '4':queue.Queue()}

@check_named_thread
def camera_source(camera_name):
    init_cam_queues('1')
    logging.critical('CAMERA NAME:%s', camera_name)
    log = logging.getLogger(str(camera_name))
    log.critical('Thread started')
    while consumers_ready.qsize() == 0:
        time.sleep(0.1)
    log.critical('Consumers dictionary ready')
    payload_size = struct.calcsize("Q")
    data = b"" 
    consumer_list = []
    camera_name = str(camera_name)

    isock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    isock.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))
    msg = {'request_type':'stream_request', 'camera_name':camera_name}
    isock.send(json.dumps(msg).encode())
    log.critical('Scoket connected')
    while True:
        while consumers[camera_name].qsize() > 0:
            log.critical('GET NEW CONSUMER:%s', len(consumer_list))
            consumer_list.append(consumers[camera_name].get())
            log.critical('APPEND NEW CONSUMER TO LIST %s', len(consumer_list))
            #log.critical('Get consumer: %s', consumer_list[-1])

        isock, frame_data, data, connection_failure = recv_package(
                                                                isock,
                                                                data, 
                                                                payload_size,
                                                                )
        if connection_failure:
            break
        #logging.debug('Frame received') 
        if consumer_list:
            #logging.debug('consumer list get')
            for consumer in consumer_list:
                if consumer[0].qsize() == 0 and consumer[1].qsize() == 0:
                    consumer[0].put(frame_data)
                elif consumer[1].qsize() > 0:
                    consumer_list.remove(consumer)
                    log.critical('Consumer removed')
        else:
            log.critical('NO consumers')
            break
    log.critical('CLOSE SOCKET')
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
"""
"""

class VideoStreamConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):      
        self.connected = True
        self.loop = asyncio.get_running_loop()
        self.sync_send = async_to_sync(self.send)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.payload_size = struct.calcsize("Q")
        self.data = b""
        super().__init__(*args, **kwargs)        

    def videostream(self):
        logging.critical('THREAD STRARTTED')
        while self.connected:
            self.sock, frame_data, self.data, connection_failure = recv_package(
                                                                self.sock,
                                                                self.data, 
                                                                self.payload_size,
                                                                )
            if not connection_failure:
                self.sync_send(frame_data.decode('utf-8'))
                logging.critical('FRAME SENDED')
            else:
                self.connected = False

    async def connect(self):
        self.camera_name = self.scope["url_route"]["kwargs"]["camera_name"]
        self.sock.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))
        msg = {'request_type':'stream_request', 'camera_name':self.camera_name}
        self.sock.send(json.dumps(msg).encode())
        logging.critical('REQUEST SENDED')

        self.connected = True
        await self.accept()   
        logging.critical('STARTING  STREAM THREAD')     
        self.loop.run_in_executor(None, self.videostream)
        #thread = threading.Thread(target=self.videostream)
        #thread.start()
        #self.videostream()
       
    async def disconnect(self, close_code):
        self.sock.close()
        logging.critical('SOCKET DISCONNECTING')
        self.connected = False
        #self.signal.put('remove consumer')
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
"""
def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function, args=args, kwargs=kwargs)
        thread.start()

    return inner

class StreamSource:

    def __init__(self):
        self.consumer_number = 0
        self.last_consumer = threading.Event()
        self.is_alive = threading.Event()
        self.consumer_queue = queue.Queue()
    
class StreamManager:

    def __init__(self):
        self.stream_source = {}
        self.is_valid = threading.Event()
        self.consumer_queue = queue.Queue()
        self.mutex = threading.Lock()

    @new_thread
    def validate_stream_sources(self):
        from .models import Camera
        stream_sources = Camera.objects.filter(is_active=True)
        self.stream_source = {}
        self.stream_source_status = {}

        for camera in stream_sources:
            self.stream_source[camera.camera_name] = StreamSource()
            self.stream_source[camera.camera_name].is_alive.set()
            self.stream_source[camera.camera_name].last_consumer.set()

        logging.critical('SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS: %s', self.stream_source.keys())
        self.is_valid.set()

    @new_thread
    def run_manager(self):
        while True:
            consumer = self.consumer_queue.get()
            logging.critical('GET NEW CONSUMER:%s', consumer.name)

            if not self.is_valid.is_set():
                self.validate_stream_sources()
                self.is_valid.wait()

            current_stream_source = self.stream_source[consumer.name]
            logging.critical('LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL %s, %s, %s',
                             current_stream_source.last_consumer.is_set(),
                             current_stream_source.is_alive.is_set(),
                             consumer.name)
            
            with self.mutex:
                if current_stream_source.last_consumer.is_set():
                    current_stream_source.is_alive.wait()
                    current_stream_source.is_alive.clear()
                    current_stream_source.last_consumer.clear()
                    logging.critical('STAAAAAAAAAAAAAAAAAAAAAAAAAART %s', consumer.name)
                    self.stream_replicator(consumer.name)

            current_stream_source.consumer_queue.put(consumer)

    @new_thread
    def stream_replicator(self, camera_name):
        log = logging.getLogger(str(camera_name))
        log.critical('Thread started ZZZZZZZZZZZZZZZZZZZZZZ%s', camera_name)
        payload_size = struct.calcsize("Q")
        data = b"" 
        consumer_list = []

        stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stream_socket.settimeout(1)
        try:
            stream_socket.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))
        except:
            self.stream_source[camera_name].is_alive.set()
            stream_socket.close()
            log.critical('FAILED TO CONNNNNNECT %s', camera_name)
            return
        
        msg = {'request_type':'stream_request', 'camera_name':camera_name}
        stream_socket.send(json.dumps(msg).encode())
        logging.critical('REQUEST SENDED XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX %s', camera_name)

        while not self.stream_source[camera_name].last_consumer.is_set():

            while self.stream_source[camera_name].consumer_queue.qsize() > 0:
                consumer_list.append(self.stream_source[camera_name].consumer_queue.get())

            stream_socket, frame_data, data = recv_package(stream_socket,
                                                           data, 
                                                           payload_size,
                                                           camera_name)
            if consumer_list and frame_data != b"":
                for consumer in consumer_list:
                    if consumer.frame.qsize() == 0 and not consumer.disconnect_event.is_set():
                        consumer.frame.put(frame_data, timeout=1)
                    elif consumer.disconnect_event.is_set():
                        log.critical('CONSUMER REMOVED DDDDDDDDDDDDDDD %s', camera_name)
                        consumer_list.remove(consumer)
            if frame_data == b"":
                log.critical('CORRRrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrRRRRUPED FRAME %s', camera_name)
                break

        stream_socket.close()
        logging.critical('STREAM ENDEEED %s', camera_name)
        self.stream_source[camera_name].is_alive.set()

manager = StreamManager()
manager.run_manager()

class Consumer:

    def __init__(self, name, frame, signal):
        self.name = name
        self.frame = frame
        self.disconnect_event = signal

class VideoStreamConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        self.pause_stream = threading.Event()
        self.disconnect_event = threading.Event()
        self.frame = queue.Queue(maxsize=1)        
        super().__init__(*args, **kwargs)

    @new_thread
    def videostream(self):
        while not self.pause_stream.is_set():
            try:
                frame = self.frame.get(timeout=10)
            except:
                self.pause_stream.set()
            else:
                self.send(frame.decode('utf-8'))

    @new_thread
    def connect(self):
        self.camera_name = str(self.scope["url_route"]["kwargs"]["camera_name"])
        if not(self.camera_name in manager.stream_source) and manager.is_valid.is_set():
            manager.is_valid.clear()
        manager.consumer_queue.put(Consumer(self.camera_name, self.frame, self.disconnect_event))
        manager.is_valid.wait()
        with manager.mutex:
            manager.stream_source[self.camera_name].consumer_number += 1

        self.videostream()       
        self.accept()

    @new_thread
    def disconnect(self, close_code):
        with manager.mutex:
            manager.stream_source[self.camera_name].consumer_number -= 1
            logging.critical('MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM%s, %s',manager.stream_source[self.camera_name].consumer_number, self.camera_name)
            if manager.stream_source[self.camera_name].consumer_number == 0:
                logging.critical('SETTING FLAG LAST CONSUMER %s', self.camera_name)
                manager.stream_source[self.camera_name].last_consumer.set()

        self.pause_stream.set()
        self.disconnect_event.set()
        self.close()
        #raise StopConsumer()
    
    @new_thread
    def receive(self, text_data):
        request = json.loads(text_data)
        signal = request['signal']
        if signal == 'pause':
            self.pause_stream.set()
        elif signal == 'play' and self.pause_stream.is_set():
            self.pause_stream.clear()
            self.videostream()

"""
#consumers = {}
#consumers_status = {}
#consumers_ready = queue.Queue(maxsize=1)

@check_named_thread
def init_cam_queues(name):
    global consumers
    from .models import Camera
    camera_list = Camera.objects.filter(is_active=True)
    logging.critical('CREATE CONSUMERS DICT')
    for camera in camera_list:
        consumers[camera.camera_name] = queue.Queue()
        logging.critical('ADD CINSUMER:%s', camera.camera_name)
    consumers_ready.put('ready')

@check_named_thread
def camera_source(camera_name):
    if consumers_ready.qsize() == 0:
        init_cam_queues('1')
    logging.critical('CAMERA NAME:%s', camera_name)
    log = logging.getLogger(str(camera_name))
    log.critical('Thread started')
    while consumers_ready.qsize() == 0:
        time.sleep(0.1)
    log.critical('Consumers dictionary ready')
    payload_size = struct.calcsize("Q")
    data = b"" 
    consumer_list = []
    camera_name = str(camera_name)

    stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    stream_socket.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))
    msg = {'request_type':'stream_request', 'camera_name':camera_name}
    stream_socket.send(json.dumps(msg).encode())

    while True:
        while consumers[camera_name].qsize() > 0:
            consumer_list.append(consumers[camera_name].get())


        stream_socket, frame_data, data, connection_failure = recv_package(
                                                                stream_socket,
                                                                data, 
                                                                payload_size,
                                                                )
        if connection_failure:
            break
 
        if consumer_list:
            for consumer in consumer_list:
                if consumer[0].qsize() == 0 and consumer[1].qsize() == 0:
                    consumer[0].put(frame_data)
                elif consumer[1].qsize() > 0:
                    consumer_list.remove(consumer)

        #else:
            #stream_socket.close()
            #break
    log.critical('STREAM ENDED %s', camera_name)





class VideoStreamConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        self.connected = True
        self.frame = queue.Queue(maxsize=1)
        self.signal = queue.Queue(maxsize=1)
        super().__init__(*args, **kwargs)        

    @new_thread
    def videostream(self):
        while self.connected:
            try:
                frame = self.frame.get(timeout=1)
            except:
                self.connected = False
            else:
                self.send(frame.decode('utf-8'))

    @new_thread
    def connect(self):
        self.camera_name = self.scope["url_route"]["kwargs"]["camera_name"]
        camera_source(self.camera_name)
        while consumers_ready.qsize() == 0:
            time.sleep(0.1)

        consumers[str(self.camera_name)].put((self.frame, self.signal))
        logging.critical('SOOOOOOOOOOOOOOCKET STAAAAAAAAAAARTTTTTT')
        self.videostream()       
        self.accept()
        
    
    @new_thread
    def disconnect(self, close_code):
        self.connected = False
        self.signal.put(close_code)
        self.close()
        raise StopConsumer()

    @new_thread
    def receive(self, text_data):
        request = json.loads(text_data)
        signal = request['signal']
        if signal == 'pause':
            self.connected = False
        elif signal == 'play' and self.connected == False:
            self.connected = True
            self.videostream()
"""