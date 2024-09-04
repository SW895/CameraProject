import asyncio
import sys
import logging
import base64
import struct
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(1, str(base_dir))
from request_builder import RequestBuilder
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
        await reader.read(self.buff_size)
        return reader, writer

    async def run(self):
        raise NotImplementedError


class StreamRequest(BaseBackendRequest):

    corrupted_frames = 0
    good_frames = 0

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='stream_request',
                                             camera_name='test_camera_1')
        self.request = builder.build()

    async def run(self):
        self.reader, self.writer = await self.get_connection(self.request)
        path = Path(__file__).resolve().parent
        with open(f"{path}/test.jpg", "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read())
        data = b''
        for i in range(1000):
            frame, data = await self.recv_packet(data)
            if frame == encoded_image:
                self.good_frames += 1
            else:
                self.corrupted_frames += 1
        return {'good_frames': self.good_frames,
                'corrupted_frames': self.corrupted_frames}

    async def recv_packet(self, data):
        payload_size = struct.calcsize("Q")
        packet = await self.reader.read(self.buff_size)
        msg_size = 0
        if packet:
            data += packet
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

        while len(data) < msg_size:
            packet = await self.reader.read(self.buff_size)
            if msg_size > 100000:
                return packet, b""
            data += packet

        frame_data = data[:msg_size]
        data = data[msg_size:]
        return frame_data, data


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


class VideoSuccessRequest(BaseBackendRequest):

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='video_request',
                                             video_name='test_video')
        self.request = builder.build()

    async def run(self):
        self.reader, self.writer = await self.get_connection(self.request)
        reply = await self.reader.read(self.buff_size)
        if reply.decode() == 'success':
            return True
        return False


class VideoFailedRequest(VideoSuccessRequest):

    def __init__(self):
        builder = RequestBuilder().with_args(request_type='video_request',
                                             video_name='abrakadabra')
        self.request = builder.build()

    async def run(self):
        return not await super().run()
