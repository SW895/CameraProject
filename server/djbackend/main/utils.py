import os
import json
import logging
import threading
import struct
import asyncio
from asgiref.sync import sync_to_async
from prometheus_client import Gauge, Summary
from .models import Camera

bytes_received = Summary(
    'djbackend_videostream_bytes_received',
    'Video stream bytes received'
)
stream_threads = Gauge(
    'djbackend_videostream_thread_number',
    'Number of videostream threads',
)
websocket_consumers = Gauge(
    'djbackend_websocket_consumer_number',
    'Number of websocket consumers',
)


def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(
            target=target_function,
            args=args,
            kwargs=kwargs)
        thread.start()
        return thread

    return inner


class VideoStreamSource:

    def __init__(self, camera_name):
        self.consumer_queue = asyncio.Queue()
        #self._mutex = asyncio.Lock()
        self._consumer_number = 0
        self.camera_name = camera_name
        self.payload_size = struct.calcsize("Q")
        self._task = None
        self.log = logging.getLogger(f'CAMERA_NAME:{camera_name}')

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['consumer_queue']
        del state['_mutex'],
        del state['_thread_working'],
        del state['_thread_dead'],
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.consumer_queue = asyncio.Queue()
        self._mutex = asyncio.Lock()

    def kill_thread(self):
        self.log.debug('Task cancelled')
        self._task.cancel()

    def run_thread(self):
        self.log.debug('Start stream')
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self.stream_source())

    def add_consumer(self):
        websocket_consumers.inc()
        self.log.debug('consumer added')
        #with self._mutex:
        self._consumer_number += 1

    def remove_consumer(self):
        websocket_consumers.dec()
        self.log.debug('consumer removed')
        #with self._mutex:
        self._consumer_number -= 1

    def consumer_number(self):
        return self._consumer_number

    def void_consumers(self):
        #with self._mutex:
            self._consumer_number = 0

    async def get_connection(self):
        try:
            self.reader, self.writer = await asyncio.open_connection(
                os.environ.get('INTERNAL_HOST', '127.0.0.1'),
                int(os.environ.get('INTERNAL_PORT', 20900))
            )
        except (asyncio.CancelledError, ConnectionRefusedError):
            return False
        self.log.debug('Connected')
        msg = {
            'request_type': 'stream_request',
            'camera_name': self.camera_name,
        }
        self.writer.write(json.dumps(msg).encode())
        await self.writer.drain()
        self.log.debug('Message sended')
        reply = await self.reader.read(65536)
        self.log.debug('Reply received')
        if reply.decode() == 'accepted':
            return True
        return False

    async def stream_source(self):
        stream_threads.inc()
        self.log.debug('Stream started')
        data = b""
        frame = b""
        consumer_list = []
        self.log.debug('Connecting ...')
        connected = await self.get_connection()

        if not connected:
            self.log.debug('Failed to connect')
            return
        self.log.debug('Successfully connected')
        try:
            while self.consumer_number() > 0:
                while self.consumer_queue.qsize() > 0:
                    consumer_list.append(await self.consumer_queue.get())
                    self.log.debug('CONSUMER RECEIVED')
                if consumer_list:
                    self.log.debug('RECEIVING PACKAGE')
                    frame, data = await self.recv_package(data)
                    self.log.debug('FRAME RECEIVED %s', len(frame))
                    if frame:
                        self.log.debug('FRAME TRUE %s', consumer_list)
                        bytes_received.observe(len(frame) + len(data))
                        for consumer in consumer_list:
                            if consumer.frame.qsize() == 0:
                                self.log.debug('PUT FRAME TO QUEUE')
                                await consumer.frame.put(frame)
                            if consumer.is_disconnected():
                                self.log.debug('DISCONNECT')
                                consumer_list.remove(consumer)
                                self.remove_consumer()
                    else:
                        self.log.debug('CORO ENDED')
                        break
        except asyncio.CancelledError:
            pass
        while self.consumer_queue.qsize() > 0:
            consumer_list.append(await self.consumer_queue.get())
        for consumer in consumer_list:
            await consumer.disconnect('1')  # ???? consumer.websocket_disconnect(msg)
        self.log.debug('FFFFFFFFFFFFF')

    async def clean_up(self):
        self.writer.close()
        await self.writer.wait_closed()
        self.void_consumers()
        stream_threads.dec()

    async def recv_package(self, data):
        try:
            self.log.debug('WAITING FOR DATA')
            packet = await asyncio.wait_for(self.reader.read(4096), 5)
        except (ConnectionResetError, BrokenPipeError, asyncio.TimeoutError):
            self.log.debug('ERRROR')
            return None, None
        if packet != b"":
            self.log.debug("PACKET RECEIVED")
            data += packet
            packed_msg_size = data[:self.payload_size]
            data = data[self.payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            while len(data) < msg_size:
                try:
                    self.log.debug('WAITING FOR DATA22222222')
                    packet = await asyncio.wait_for(self.reader.read(1048576), 5)
                except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError, asyncio.TimeoutError):
                    return None, None
                if packet == b"":
                    self.log.error('BAD FRAME')
                    return None, None
                if msg_size > 100000:
                    self.log.error('BAD FRAME')
                    return packet, b""
                data += packet

            frame_data = data[:msg_size]
            data = data[msg_size:]
            return frame_data, data
        return None, None


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class VideoStreamManager(metaclass=Singleton):

    def __init__(self):
        self.stream_sources = {}
        self.consumer_queue = asyncio.Queue()
        self._task = None
        self.log = logging.getLogger('STREAM MANAGER')
        self._running = False

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['consumer_queue']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.consumer_queue = asyncio.Queue()

    def kill_manager(self):
        self._task.cancel()

    async def validate_stream_sources(self):
        self.log.debug('VALIDATING')
        stream_sources = await sync_to_async(Camera.objects.filter)(is_active=True)
        #self.log.debug('ZZZZZZZZZZZZZZZZZZZZZZZZZZZ %s', len(stream_sources))
        self.stream_sources.clear()
        async for source in stream_sources:
            self.log.debug('CREATE SOURCE')
            self.stream_sources[source.camera_name] = VideoStreamSource(
                source.camera_name
            )

    def run_manager(self):
        if self._running:
            return
        self.log.debug('GET EVENT LOOP')
        loop = asyncio.get_event_loop()
        self.log.debug('GOT EVENT LOOP %s', loop)
        self._task = loop.create_task(self.run())
        self._running = True
        self.log.debug('CREATE TASK %s', self._task)

    async def run(self):
        self.log.debug('Manager started')
        while True:
            try:
                self.log.debug('WAITING FOR CONSUMER')
                consumer = await self.consumer_queue.get()
                self.log.debug('GOT CONSUMER')
            except asyncio.CancelledError:
                break
            self.log.debug('Get consumer')
            if not (consumer.camera_name in self.stream_sources):
                self.log.debug('VALIDATING STREAM SOURCES')
                await self.validate_stream_sources()

            current_stream_source = self.stream_sources[consumer.camera_name]

            if current_stream_source.consumer_number() == 0:
                self.log.debug('START NEW CORO')
                #current_stream_source.kill_thread()
                current_stream_source.add_consumer()
                await current_stream_source.consumer_queue.put(consumer)
                current_stream_source.run_thread()
            else:
                self.log.debug('CORO ALREADY RUNNING')
                current_stream_source.add_consumer()
                current_stream_source.consumer_queue.put(consumer)
