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
    
    def __init__(self, camera_name):
        self.consumer_queue = queue.Queue()
        self._mutex = threading.Lock()
        self._thread_working = threading.Event()
        self._thread_working.set()
        self._thread_dead = threading.Event()
        self._thread_dead.set()
        self._consumer_number = 0
        self.camera_name = camera_name
        self.payload_size = struct.calcsize("Q")
        self.stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream_socket.settimeout(5.0)

    def thread_dead(self):
        self._thread_dead.set()   

    def thread_working(self):
        return self._thread_working.is_set()

    def kill_thread(self):
        self._thread_working.clear()
        self._thread_dead.wait()
    
    def run_thread(self):
        self._thread_working.set()
        self._thread_dead.clear()
        self.stream_source()
    
    def add_consumer(self):
        with self._mutex:
            self._consumer_number += 1

    def remove_consumer(self):
        with self._mutex:
            self._consumer_number -= 1

    def consumer_number(self):
        return self._consumer_number
    
    def void_consumers(self):
        with self._mutex:
            self._consumer_number = 0
    
    def get_connection(self):
        self.stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream_socket.settimeout(5.0)
        try:
            self.stream_socket.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'), int(os.environ.get('INTERNAL_PORT', 20900))))
        except:
            self.thread_dead()
            self.stream_socket.close()
            return False
        msg = {'request_type':'stream_request', 'camera_name':self.camera_name}
        self.stream_socket.send(json.dumps(msg).encode())
        return True

    @new_thread
    def stream_source(self):
        data = b"" 
        frame = b""
        consumer_list = []
        connected = self.get_connection()

        if connected:
            while self.thread_working() and (self.consumer_number() > 0):
                while self.consumer_queue.qsize() > 0:
                    consumer_list.append(self.consumer_queue.get())
                if consumer_list:
                    frame, data = self.recv_package(data)
                    if frame:
                        for consumer in consumer_list:
                            if consumer.frame.qsize() == 0:
                                consumer.frame.put(frame)
                            if consumer.is_disconnected():
                                consumer_list.remove(consumer)
                                self.remove_consumer()
                    else:
                        break
            self.stream_socket.close()
        
        for consumer in consumer_list:
            consumer.disconnect('1') #????????
        self.void_consumers()
        self.thread_dead()
   
    def recv_package(self, data):
        try:
            packet = self.stream_socket.recv(4096)
        except:
            return None, None
        if packet != b"":
            data += packet
            packed_msg_size = data[:self.payload_size]
            data = data[self.payload_size:]
            msg_size = struct.unpack("Q",packed_msg_size)[0]

            while len(data) < msg_size:
                try:
                    packet = self.stream_socket.recv(1048576)
                except:
                    return None, None
                if (not self.thread_working()) or packet == b"":
                    return None, None
                if msg_size > 100000:
                    return packet, b""
                data += packet

            frame_data = data[:msg_size]
            data  = data[msg_size:]
            return frame_data, data
        
        return None, None


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
            self.stream_sources[source.camera_name] = VideoStreamSource(source.camera_name)
        self.stream_sources_valid()
    
    @new_thread
    def run_manager(self):
        while True:
            consumer = self.consumer_queue.get()
            if not self.is_valid():
                self.validate_stream_sources()
                self.wait_validation()            
            current_stream_source = self.stream_sources[consumer.camera_name]
            current_stream_source.consumer_queue.put(consumer)

            if current_stream_source.consumer_number() == 0:
                current_stream_source.kill_thread()
                current_stream_source.add_consumer()
                current_stream_source.run_thread()
            else:
                current_stream_source.add_consumer()
