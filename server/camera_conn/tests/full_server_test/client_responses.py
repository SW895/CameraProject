import asyncio
import sys
import json
import time
import base64
import struct
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(1, str(base_dir))
from request_builder import RequestBuilder
from settings import (EXTERNAL_HOST,
                      EXTERNAL_PORT,
                      SOCKET_BUFF_SIZE)


class TestClient:

    background_tasks = set()

    def set_signal_connection(self, signal_conn):
        self._signal_conn = signal_conn

    @property
    def result(self):
        return self._signal_conn.results

    async def result_ready(self):
        while not self._signal_conn.wait_result.is_set():
            await asyncio.sleep(1)

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
        reader, writer = await asyncio.open_connection(
            self.host, self.port)

        writer.write(request.serialize().encode())
        await writer.drain()

        reply = await reader.read(self.buff_size)
        if reply.decode() == 'accepted':
            return reader, writer
        return None, None


class SignalConnection(BaseConnection):

    handlers = []
    results = {}
    wait_result = asyncio.Event()

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='signal')
        self.request = builder.build()

    def add_handlers(self, *args):
        for handler in args:
            self.handlers.append(handler)

    async def run(self):
        self.wait_result.clear()
        while True:
            reader, _ = await self.get_connection(self.request)
            if not reader:
                await asyncio.sleep(0.5)
                continue
            try:
                data = await reader.read(self.buff_size)
            except asyncio.CancelledError:
                return
            if data:
                msg_list = data.decode().split('\n')
                for message in msg_list:
                    if not message:
                        continue
                    builder = RequestBuilder().with_args(**json.loads(message))
                    request = builder.build()
                    for handler in self.handlers:
                        result = await handler.run(request)
                        if isinstance(result, dict):
                            self.results.update(result)
                            self.wait_result.set()
                            return
                break
            else:
                await asyncio.sleep(0.5)


class StreamConnection(BaseConnection):

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='stream_response',
                                             camera_name='test_camera_1')
        self.request = builder.build()

    async def run(self, request):
        if request.request_type != 'stream_request':
            return
        _, writer = await self.get_connection(self.request)
        path = Path(__file__).resolve().parent
        with open(f"{path}/test.jpg", "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read())
        message = struct.pack("Q", len(encoded_image)) + encoded_image
        while True:
            try:
                writer.write(message)
                await writer.drain()
            except Exception:
                return


class UserAproveResponse(BaseConnection):

    def __init__(self):
        record = {'username': 'test_user',
                  'request_result': 'aproved'}
        self.record = json.dumps(record) + '\n'
        builder = RequestBuilder()\
            .with_args(request_type='aprove_user_response',
                       record_size=len(self.record))
        self.request = builder.build()

    async def run(self, request):
        if request.request_type != 'aprove_user_request':
            return
        reader, writer = await self.get_connection(self.request)
        writer.write(self.record.encode())
        await writer.drain()
        reply = await reader.read(self.buff_size)
        response = json.loads(reply.decode())
        if response['status'] == 'success':
            result = True
        else:
            result = False
        return {request.request_type.upper().replace('_', ' '): result}


class VideoResponse(BaseConnection):

    def __init__(self):
        path = Path(__file__).resolve().parent
        with open(f"{path}/test.jpg", "rb") as video_file:
            self.file = video_file.read()
            video_size = len(self.file)
        builder = RequestBuilder().with_args(request_type='video_response',
                                             video_name='test_video',
                                             video_size=video_size)
        self.request = builder.build()

    async def run(self, request):
        if request.request_type != 'video_request':
            return
        if request.video_name == 'test_video':
            reader, writer = await self.get_connection(self.request)
            writer.write(self.file)
            await writer.drain()
