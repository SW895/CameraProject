import asyncio
import logging
import json
from settings import (
    GET_SERVER_EVENTS_TIMEOUT,
    CAMERA_LIST,
    RECONNECTION_TIMEOUT
)
from utils import RequestBuilder
from connection_handlers import ConnectionMixin
from PyQt6.QtCore import QObject


class ConnectionClient(ConnectionMixin, QObject):

    handlers = []
    log = logging.getLogger('Connection Client')

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='signal')
        self.request = builder.build()

    def add_handler(self, *args):
        for handler in args:
            self.handlers.append(handler)

    def run_client(self):
        task = self.loop.create_task(self._run_client())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        self.loop.run_forever()

    async def _run_client(self):
        await self.register_client()
        await self.get_server_events()

    async def get_server_events(self):
        while True:
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

                for message in msg_list:
                    builder = RequestBuilder().with_args(**json.loads(message))
                    request = builder.build()
                    for handler in self.handlers:
                        result = await handler.handle(request)
                        if result:
                            break
                    else:
                        self.log.info('Wrong request type')
            try:
                asyncio.sleep(GET_SERVER_EVENTS_TIMEOUT)
            except asyncio.CancelledError:
                return

    async def register_client(self):
        records = ''
        for camera in CAMERA_LIST:
            record = {'camera_name': camera}
            records += json.dumps(record) + "\n"

        builder = RequestBuilder().with_args(request_type='new_camera_record',
                                             record_size=len(records))
        request = builder.build()

        while True:
            reply = await self.send_records(request, records)
            if reply:
                break
            try:
                asyncio.sleep(RECONNECTION_TIMEOUT)
            except asyncio.CancelledError:
                return

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
