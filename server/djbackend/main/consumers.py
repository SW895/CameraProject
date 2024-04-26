import socket
import asyncio
import queue
import os
import json
import struct
from .utils import check_named_thread, recv_package

from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.exceptions import StopConsumer
import logging
import threading

import time

logging.basicConfig(level=logging.DEBUG,
                    format="%(name)s | %(levelname)s | %(asctime)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                    )


def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function, args=args, kwargs=kwargs)
        thread.start()

    return inner


class VideoStreamSource:
    
    def __init__(self):
        self.consumer_queue = queue.Queue()
        self._mutex = threading.Lock()
        self._thread_working = threading.Event()
        self._thread_working.set()
        self._thread_dead = threading.Event()
        self._thread_dead.set()
        self._consumer_number = 0

    def thread_dead(self):
        with self._mutex:
            self._thread_dead.set()   

    def thread_working(self):
        with self._mutex:
            return self._thread_working.is_set()

    def kill_thread(self):
        with self._mutex:
            self._thread_working.clear()
        logging.critical('FLAG TO STOP LOOP')
        self._thread_dead.wait()
    
    def wait_thread(self):
        self._thread_dead.wait()
    
    def run_thread(self, camera_name):
        with self._mutex:
            self._thread_working.set()
        self.restore_flag()
        self.stream_source(camera_name)

    #def wait_thread_end(self):
        #self._thread_dead.wait()
    
    def restore_flag(self):
        with self._mutex:
            self._thread_dead.clear()
    
    def add_consumer(self):
        with self._mutex:
            self._consumer_number += 1

    def remove_consumer(self):
        with self._mutex:
            self._consumer_number -= 1

    def consumer_number(self):
        with self._mutex:
            return self._consumer_number
    
    @new_thread
    def stream_source(self, camera_name):

        log = logging.getLogger(str(camera_name))
        log.critical('Thread started ZZZZZZZZZZZZZZZZZZZZZZ%s', camera_name)
        payload_size = struct.calcsize("Q")
        data = b"" 
        frame_data = b""

        frame_data = "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"
        frame_data = frame_data.encode("utf-8")
        consumer_list = []

        stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stream_socket.settimeout(1)
        
        try:
            stream_socket.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))
        except:
            self.thread_dead()
            stream_socket.close()
            log.critical('FAILED TO CONNNNNNECT %s', camera_name)
            return
        
        msg = {'request_type':'stream_request', 'camera_name':camera_name}
        stream_socket.send(json.dumps(msg).encode())
        logging.critical('REQUEST SENDED XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX %s', camera_name)

        while self.thread_working():

            while self.consumer_queue.qsize() > 0:
                logging.critical('STREAM SOURCE GET CONSUMER %s', camera_name)
                consumer_list.append(self.consumer_queue.get())
            #log.critical('CONSUMERS APPEDNDED %s', camera_name)
            if consumer_list:
                #logging.critical('GETTING FRAME %s', camera_name)
                stream_socket, frame_data, data = self.recv_package(stream_socket,
                                                                    data, 
                                                                    payload_size,
                                                                    camera_name,)
                #logging.critical('FRAME RECEIVED %s', camera_name)
                for consumer in consumer_list:
                    #log.critical('TRY TO PUT FRAME TO CONSUMER %s', camera_name)
                    if consumer.frame.qsize() == 0:
                        #log.critical('PUT FRAME TO CONSUMER %s', camera_name)
                        consumer.frame.put(frame_data)
                    #log.critical('CHECK IF CONSUMER DISCONNECTED %s', camera_name)
                    if consumer.is_disconnected():
                        log.critical('CONSUMER REMOVED DDDDDDDDDDDDDDD %s', camera_name)
                        consumer_list.remove(consumer)
            #else:
                #time.sleep(3)
                #logging.critical('NO CONSUMERS %s %s %s', camera_name, self.consumer_number(), self.thread_working())

        stream_socket.close()
        logging.critical('STREAM ENDEEEEEEEEEEEEEEEEEEEED %s', camera_name)
        self.thread_dead()
        logging.critical('STREAM ENDEEeeeeeeeeeeeeeeeeeED %s', camera_name)

    def recv_package(self, connection, data, payload_size, camera_name):
        frame_data = b""
        #logging.critical('QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQRECEIVING PACKAGE %s', camera_name)
        try:
            packet = connection.recv(4096)
        except:
            pass
        else:   
            if packet != b"":
                data += packet   
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q",packed_msg_size)[0]

                while len(data) < msg_size:
                    #logging.critical('QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQRECEIVING DATA FRAME %s', camera_name) #!!!!!!!!!!!!!!!!!! ОШИБКА ТУТ ТЫ ЕБАНАТ ИЗ ЦИКЛА НЕ ВЫХОДИШЬ
                    try:
                        packet = connection.recv(1048576)
                    except:
                        break
                    else:
                        if not self.thread_working():
                            break
                        if packet == b"":
                            break
                        data += packet

                frame_data = data[:msg_size]
                data  = data[msg_size:]
        #logging.critical('QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQFRAME RECEIVED %s', camera_name)
        return connection, frame_data, data

class VideoStreamManager:

    def __init__(self):
        self.stream_sources = {}
        self.consumer_queue = queue.Queue()
        self._valid = threading.Event()
        #self._mutex = threading.Lock()
    
    def is_valid(self):
        return self._valid.is_set()

    def stream_sources_valid(self):
        self._valid.set()

    def stream_sources_invalid(self):
        self._valid.clear()
    
    def wait_validation(self):
        self._valid.wait()

    @new_thread
    def validate_stream_sources(self):
        from .models import Camera
        stream_sources = Camera.objects.filter(is_active=True)
        self.stream_sources.clear()

        for source in stream_sources:
            self.stream_sources[source.camera_name] = VideoStreamSource()

        logging.critical('SSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS: %s', self.stream_sources.keys())
        self.stream_sources_valid()
    
    @new_thread
    def run_manager(self):
        while True:
            consumer = self.consumer_queue.get()
            logging.critical('GET NEW CONSUMER %s', consumer.camera_name)
            if not self.is_valid():
                self.validate_stream_sources()
                self.wait_validation()
            
            current_stream_source = self.stream_sources[consumer.camera_name]            

            if current_stream_source.consumer_number() <= 1:
                logging.critical('KILLING THREAD %s', consumer.camera_name)
                current_stream_source.kill_thread()
                logging.critical('THREAD KILLED, RUNNING NEW %s',consumer.camera_name)
                current_stream_source.run_thread(consumer.camera_name)
            
            logging.critical('PUTTING CONSUMER TO SOURCE QUEUE %s', consumer.camera_name)
            current_stream_source.consumer_queue.put(consumer)


class VideoStreamConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        self._pause_stream = threading.Event()
        self._mutex = threading.Lock()
        self._disconnected = threading.Event()
        self.frame = queue.Queue(maxsize=1)        
        super().__init__(*args, **kwargs)

    def is_disconnected(self):
        #with self._mutex:
            return self._disconnected.is_set()
    
    def end_consumer(self):
        with self._mutex:
            self._disconnected.set()

    def pause_stream(self):
        with self._mutex:
            self._pause_stream.set()
    
    def play_stream(self):
        with self._mutex:
            self._pause_stream.clear()

    def is_paused(self):
        with self._mutex:
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
        self.camera_name = str(self.scope["url_route"]["kwargs"]["camera_name"])
        if not(self.camera_name in manager.stream_sources) and manager.is_valid():
            manager.stream_sources_invalid()

        manager.consumer_queue.put(self)
        manager.wait_validation()
        manager.stream_sources[self.camera_name].add_consumer()
        self.videostream()       
        self.accept()

    @new_thread
    def disconnect(self, close_code):
        manager.stream_sources[self.camera_name].remove_consumer()
        logging.critical('MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM  %s',self.camera_name)
        self.pause_stream()
        logging.critical('NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN CONSUMER STREAM PAUSED %s',self.camera_name)
        self.end_consumer()
        logging.critical('NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNN CONSUMER DISCONNECTED %s, %s',self.camera_name, self._disconnected.is_set())
        
        self.close()
        #raise StopConsumer()
    
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