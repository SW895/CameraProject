import logging
import asyncio
from request_builder import RequestBuilder
from utils import (
    ConnectionMixin,
    Singleton,
)


class VideoStreamManager(metaclass=Singleton):

    requesters = asyncio.Queue()
    cameras = {}
    log = logging.getLogger('Stream manager')

    def update_camera_list(self, camera_list):
        for camera in camera_list:
            self.cameras.update(
                {camera: VideoStream(camera_worker=camera_list[camera],
                                     camera_name=camera)})

    def set_event_loop(self, loop):
        self.loop = loop

    async def run_manager(self):
        while True:
            self.log.debug('Waiting for stream requester')
            try:
                requester = await self.requesters.get()
            except asyncio.CancelledError:
                break
            self.requesters.task_done()
            self.log.debug('Get requester %s, %s',
                           requester.camera_name,
                           self.cameras)
            try:
                current_channel = self.cameras[requester.camera_name]
            except KeyError:
                self.log.error('No such camera')
                continue

            self.log.debug('Starting channel')
            await self.run_channel(current_channel)

    async def run_channel(self, current_channel):
        if current_channel.task:
            self.log.debug('Cancelling task')
            current_channel.task.cancel()
            await current_channel.task

        self.log.debug('START COURUTINE')
        current_channel.task = self.loop.create_task(
            current_channel.stream_video())


class VideoStream(ConnectionMixin):

    task = None

    def __init__(self, camera_worker, camera_name):
        self.camera_worker = camera_worker
        self.camera_name = camera_name
        self.log = logging.getLogger(self.camera_name)
        builder = RequestBuilder().with_args(request_type='stream_response',
                                             camera_name=self.camera_name)
        self.request = builder.build()

    async def stream_video(self):
        self.log.debug('Connecting to server')
        reader, writer = await self.connect_to_server(self.request)
        if not writer:
            self.log.error('Failed to connect to server')
        else:
            self.log.debug('Connected to server. Stream begin')
        while writer:
            try:
                encoded_frame = await \
                    self.camera_worker.videostream_frame.get()
            except asyncio.CancelledError:
                writer.close()
                await writer.wait_closed()
                break
            self.camera_worker.videostream_frame.task_done()
            try:
                writer.write(encoded_frame)
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                self.log.error('Connection to server lost')
                break
        self.task = None
