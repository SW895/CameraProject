import asyncio
import sys
import logging
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(1, str(base_dir))
from cam_server import RequestBuilder
from settings import (INTERNAL_HOST,
                      INTERNAL_PORT,
                      SOCKET_BUFF_SIZE,)
from db import connect_to_db


class BaseBackendRequest:

    host = INTERNAL_HOST
    port = INTERNAL_PORT
    buff_size = SOCKET_BUFF_SIZE

    async def get_connection(self, request):
        reader, writer = await asyncio.open_connection(
                        self.host, self.port)

        writer.write(request.serialize().encode())
        await writer.drain()

        return reader, writer

    async def run(self):
        reader, writer = await self.get_connection(self.request)
        return await reader.read(self.buff_size)


class StreamRequest(BaseBackendRequest):

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='stream_request',
                                             camera_name='test_camera_1')
        self.request = builder.build()


class AproveUserRequest(BaseBackendRequest):

    def __init__(self):
        builder = RequestBuilder() \
            .with_args(request_type='aprove_user_request',
                       username='test_user')
        self.request = builder.build()

    async def run(self):
        db_conn, cur = await connect_to_db()
        try:
            await cur.execute("INSERT INTO registration_customuser \
                          (password, \
                          date_joined, \
                          is_superuser, \
                          first_name, \
                          last_name, \
                          is_staff, \
                          is_active, \
                          email, \
                          admin_checked, \
                          username) \
                           VALUES \
                          ('test_password', \
                           timestamp '2020-01-01 00:00:00.001', \
                           False, \
                           'first', \
                           'last', \
                           False, \
                           False, \
                           'test@email.com', \
                           False, \
                           'test_user') ;",)
        except Exception as error:
            logging.error('%s', error)
        await db_conn.commit()
        await self.get_connection(self.request)
