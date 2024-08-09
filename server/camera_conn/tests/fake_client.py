import asyncio
import json
import sys
import time
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(base_dir))
from cam_server import RequestBuilder
from settings import (EXTERNAL_HOST,
                      EXTERNAL_PORT,
                      SOCKET_BUFF_SIZE)
import logging

TEST_CAMERA_NUM = 2


class TestClient:

    background_tasks = set()

    def set_signal_connection(self, signal_conn):
        self._signal_conn = signal_conn

    def add_handlers(self, *args):
        self._signal_conn.add_handlers(*args)

    def prepare_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        task = self.loop.create_task(self._signal_conn.run())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    def run_client(self):
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


class BaseConnection:

    host = EXTERNAL_HOST
    port = EXTERNAL_PORT
    buff_size = SOCKET_BUFF_SIZE

    async def run(self):
        raise NotImplementedError

    async def get_connection(self, request):
        logging.debug('GETTING CONNECTION')
        reader, writer = await asyncio.open_connection(
                        self.host, self.port)

        writer.write(request.serialize().encode())
        await writer.drain()

        reply = await reader.read(self.buff_size)
        if reply.decode() == 'accepted':
            return reader, writer


class SignalConnection(BaseConnection):
    handlers = []

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='signal')
        self.request = builder.build()

    def add_handlers(self, *args):
        for handler in args:
            self.handlers.append(handler)

    async def run(self):
        reader, writer = await self.get_connection(self.request)
        while True:
            try:
                data = await reader.read(self.buff_size)
            except asyncio.CancelledError:
                logging.debug('CORO FINISHED cancelled')
                return
            if data:
                builder = RequestBuilder().with_bytes(data)
                request = builder.build()
                for handler in self.handlers:
                    result = await handler.run(request)
                    if result:
                        break
            else:
                logging.debug('CORO FINISHED')
                return


class RegisterCameras(BaseConnection):

    def __init__(self):
        cam_list = []
        for test_camera in range(TEST_CAMERA_NUM):
            camera_name = f'test_camera_{test_camera}'
            cam_list.append({'camera_name': camera_name})
        self.record = ''
        for item in cam_list:
            self.record += json.dumps(item) + '\n'

        builder = RequestBuilder().with_args(request_type='new_camera_record',
                                             record_size=len(self.record))
        self.request = builder.build()

    async def run(self):
        reader, writer = await self.get_connection(self.request)
        writer.write(self.record.encode())
        await writer.drain()
        reply = await reader.read(self.buff_size)
        writer.close()
        await writer.wait_closed()
        return reply.decode()


class StreamConnection(BaseConnection):

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='stream_response',
                                             camera_name='test_camera_1')
        self.request = builder.build()

    async def run(self):
        reader, writer = await self.get_connection(self.request)
        for i in range(10):
            writer.write(bytes(1000))
            await writer.drain()
