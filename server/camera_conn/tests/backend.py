import asyncio
import sys
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(base_dir))
from cam_server import RequestBuilder
from settings import (INTERNAL_HOST,
                      INTERNAL_PORT,
                      SOCKET_BUFF_SIZE)


class BaseBackendRequest:

    host = INTERNAL_HOST
    port = INTERNAL_PORT
    buff_size = SOCKET_BUFF_SIZE

    async def run(self):
        raise NotImplementedError

    async def get_connection(self, request):
        # loop = asyncio.get_running_loop()
        reader, writer = await asyncio.open_connection(
                        self.host, self.port)

        writer.write(request.serialize().encode())
        await writer.drain()

        return reader, writer


class StreamRequest(BaseBackendRequest):

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='stream_request',
                                             camera_name='test_camera_1')
        self.request = builder.build()

    async def run(self):
        reader, writer = await self.get_connection(self.request)
        return await reader.read(self.buff_size)
