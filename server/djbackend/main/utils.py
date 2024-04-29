import os
import json
import socket
import queue
import threading
import struct


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
        self._thread_dead.set()   

    def thread_working(self):
        return self._thread_working.is_set()

    def kill_thread(self):
        self._thread_working.clear()
        self._thread_dead.wait()
    
    def run_thread(self, camera_name):
        self._thread_working.set()
        self._thread_dead.clear()
        self.stream_source(camera_name)
    
    def add_consumer(self):
        with self._mutex:
            self._consumer_number += 1

    def remove_consumer(self):
        with self._mutex:
            self._consumer_number -= 1

    def consumer_number(self):
        with self._mutex:
            return self._consumer_number
    
    def get_connection(self, camera_name):
        stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stream_socket.settimeout(1)
        
        try:
            stream_socket.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))
        except:
            self.thread_dead()
            stream_socket.close()
            return None
        
        msg = {'request_type':'stream_request', 'camera_name':camera_name}
        stream_socket.send(json.dumps(msg).encode())
        return stream_socket

    @new_thread
    def stream_source(self, camera_name):
        payload_size = struct.calcsize("Q")
        data = b"" 
        frame = b""
        consumer_list = []
        stream_socket = self.get_connection(camera_name)

        while self.thread_working() and stream_socket and (self.consumer_number() > 0):

            while self.consumer_queue.qsize() > 0:
                consumer_list.append(self.consumer_queue.get())
            if consumer_list:
                stream_socket, frame, data = self.recv_package(stream_socket,
                                                                data, 
                                                                payload_size,)
                if frame:
                    for consumer in consumer_list:
                        if consumer.frame.qsize() == 0:
                            consumer.frame.put(frame)
                        if consumer.is_disconnected():
                            consumer_list.remove(consumer)
                else:
                    for consumer in consumer_list:
                        consumer.disconnect('1') #????????
                    break

        stream_socket.close()
        self.thread_dead()

    def recv_package(self, connection, data, payload_size):
        frame_data = b""
        try:
            packet = connection.recv(4096)
        except:
            return connection, None, None
        else:   
            if packet != b"":
                data += packet   
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q",packed_msg_size)[0]

                while len(data) < msg_size:
                    try:
                        packet = connection.recv(1048576)
                    except:
                        return connection, None, None
                    else:
                        if not self.thread_working() or packet == b"":
                            break
                        data += packet

                frame_data = data[:msg_size]
                data  = data[msg_size:]
            
        return connection, frame_data, data


class VideoStreamManager:

    def __init__(self):
        self.stream_sources = {}
        self.consumer_queue = queue.Queue()
        self._valid = threading.Event()
    
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

        self.stream_sources_valid()
    
    @new_thread
    def run_manager(self):
        while True:
            consumer = self.consumer_queue.get()
            if not self.is_valid():
                self.validate_stream_sources()
                self.wait_validation()
            
            current_stream_source = self.stream_sources[consumer.camera_name]            

            if current_stream_source.consumer_number() <= 1:
                current_stream_source.kill_thread()
                current_stream_source.run_thread(consumer.camera_name)
            
            current_stream_source.consumer_queue.put(consumer)