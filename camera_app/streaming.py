import logging
import asyncio
from request_builder import RequestBuilder
from utils import (
    ConnectionMixin,
    Singleton,
)


class WorkerObject:

    def __init__(self, camera_worker, channel):
        self.camera_worker = camera_worker
        self.channel = channel


class VideoStreamManager(metaclass=Singleton):

    requesters = asyncio.Queue()
    cameras = {}
    log = logging.getLogger('Stream manager')

    def __init__(self, camera_list=None):
        if camera_list:
            for camera in camera_list:
                self.cameras.update(
                    {camera: WorkerObject(camera_worker=camera,
                                          channel=VideoStream(camera.name))})

    async def process_requesters(self):
        while True:
            self.log.debug('Waiting for stream requester')
            try:
                requester = await self.requesters.get()
            except asyncio.CancelledError:
                break
            self.requesters.task_done()

            try:
                current_channel = self.cameras[requester.camera_name]
            except KeyError:
                self.log.error('No such camera')
                continue

            self.log.debug('Starting channel')
            await self.run_channel(current_channel.camera_worker.frame_source)

    async def run_channel(self, camera):
        if camera.task:
            self.log.debug('Cancelling task')
            camera.task.cancel()
            await camera.task

        self.log.debug('START COURUTINE')
        camera.task = self.loop.create_task(camera.stream_video())


class VideoStream(ConnectionMixin):

    task = None

    def _init__(self, camera_name):
        self.camera_name = camera_name
        self.log = logging.getLogger(self.camera_name)
        builder = RequestBuilder().with_args(request_type='stream_source',
                                             camera_name=self.camera_name)
        self.request = builder.build()

    async def stream_video(self, frame_source):
        self.log.debug('Connecting to server')
        reader, writer = self.connect_to_server(self.request)
        if not writer:
            self.log.error('Failed to connect to server')
        else:
            self.log.debug('Connected to server. Stream begin')
        while writer:
            try:
                encoded_frame = await frame_source.get()
            except asyncio.CancelledError:
                writer.close
                await writer.wait_closed()
                break
            frame_source.task_done()
            try:
                writer.write(encoded_frame)
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                self.log.error('Connection to server lost')
                break
        self.task = None
