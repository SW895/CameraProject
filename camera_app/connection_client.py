import asyncio
import logging
import json
import time
from settings import (
    GET_SERVER_EVENTS_TIMEOUT,
    CAMERA_LIST,
    RECONNECTION_TIMEOUT,
)
from request_builder import RequestBuilder
from utils import ConnectionMixin
from streaming import VideoStreamManager
from PyQt6.QtCore import QObject, pyqtSignal


class ConnectionClient(ConnectionMixin, QObject):

    handlers = []
    connection_status = pyqtSignal(bool)
    event_loop_created = pyqtSignal()
    finished = pyqtSignal()
    log = logging.getLogger('Connection Client')

    def __init__(self, camera_workers_list):
        super().__init__()
        self.log.debug('Init connection client')
        self.stream_manager = VideoStreamManager(camera_workers_list)
        builder = RequestBuilder().with_args(request_type='signal')
        self.request = builder.build()

    def add_handlers(self, *args):
        self.log.debug('Add handler')
        for handler in args:
            self.handlers.append(handler)

    def run_client(self):
        self.log.debug('Running connection client')
        self.loop = asyncio.new_event_loop()
        self.log.debug('Event loop created')
        self.background_tasks.add(
            self.loop.create_task(self.register_client()))
        self.background_tasks.add(
            self.loop.create_task(self.stream_manager.run_manager()))
        for task in self.background_tasks:
            task.add_done_callback(self.background_tasks.discard)
        self.log.debug('Tasks added')
        self.event_loop_created.emit()
        self.loop.run_forever()

    def shutdown(self):
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            while self.loop.is_running():
                time.sleep(0.1)
        tasks = asyncio.all_tasks(loop=self.loop)
        if tasks:
            for task in tasks:
                task.cancel()
            group = asyncio.gather(*tasks, return_exceptions=True)
            self.loop.run_until_complete(group)
        self.loop.close()
        self.finished.emit()

    async def register_client(self):
        records = ''
        for camera in CAMERA_LIST:
            record = {'camera_name': camera}
            records += json.dumps(record) + "\n"

        builder = RequestBuilder().with_args(request_type='new_camera_record',
                                             record_size=len(records))
        request = builder.build()
        self.log.debug('REGISTER CLIENT')
        while True:
            reply = await self.send_records(request, records)
            if reply:
                self.log.debug('CLIENT REGISTERED')
                break
            self.connection_status.emit(False)
            try:
                await asyncio.sleep(RECONNECTION_TIMEOUT)
            except asyncio.CancelledError:
                self.log.debug('TASK CANCELLED')
                return
        task = self.loop.create_task(self.get_server_events())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    async def send_records(self, request, records):
        reader, writer = await self.connect_to_server(request)
        if writer:
            try:
                writer.write(records.encode())
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                self.log.error('Connection Error')
            else:
                reply = await reader.read(self.buff_size)
                response = json.loads(reply.decode())
                if response['status'] == 'success':
                    return True
                writer.close()
                await writer.wait_closed()
        return False

    async def get_server_events(self):
        while True:
            self.log.debug('CONNECTING TO READ SERVER EVENTS')
            reader, writer = await self.connect_to_server(self.request)
            if writer:
                messages = b""
                while True:
                    self.log.info('Waiting for a message')
                    data = await reader.read(self.buff_size)
                    if not data:
                        break
                    messages += data
                self.log.debug('Messages received')
                msg_list = messages.decode().split('\n')
                self.log.debug('SERVER EVENTS RECEIVED: %s', msg_list)
                self.connection_status.emit(True)
                for message in msg_list:
                    builder = RequestBuilder().with_args(**json.loads(message))
                    request = builder.build()
                    for handler in self.handlers:
                        result = await handler.handle(request, self.loop)
                        if result:
                            break
                    else:
                        self.log.info('Wrong request type')
            else:
                self.connection_status.emit(False)
            try:
                await asyncio.sleep(GET_SERVER_EVENTS_TIMEOUT)
            except asyncio.CancelledError:
                return
