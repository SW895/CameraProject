import asyncio
import logging
from .camera_utils import ServerRequest, SingletonMeta
from .db import ActiveCameras


class BaseManager:

    responses = asyncio.Queue()
    requesters = asyncio.Queue()

    @classmethod
    def set_signal_handler(self, signal_handler):
        self._signal_hander = signal_handler

    async def run_manager(self):
        self.log.info('Starting manager')
        self.loop = asyncio.get_running_loop()
        self.loop.create_task(self.process_requesters())
        self.loop.create_task(self.process_responses())

    async def process_requesters(self):
        raise NotImplementedError

    async def process_responses(self):
        raise NotImplementedError

    @classmethod
    async def send_request(self, signal):
        await self._signal_hander.signal_queue.put(signal)


class VideoStreamManager(BaseManager, metaclass=SingletonMeta):

    stream_channels = {}
    log = logging.getLogger('VideoStream Manager')

    async def process_requesters(self):
        while True:
            self.log.debug('Waiting for stream requester')
            try:
                requester = await self.requesters.get()
            except asyncio.CancelledError:
                break

            try:
                current_channel = self.stream_channels[requester.camera_name]
            except KeyError:
                await self.update_stream_channels()
                current_channel = self.stream_channels[requester.camera_name]

            self.log.debug('Get stream requester')
            await current_channel.add_consumer(requester)
            self.requesters.task_done()
            self.log.debug('Starting channel')
            self.loop.create_task(self.run_channel(current_channel))

    async def process_responses(self):
        while True:
            self.log.debug('Waiting for a stream source')
            try:
                source = await self.responses.get()
            except asyncio.CancelledError:
                break
            try:
                current_channel = self.stream_channels[source.camera_name]
            except KeyError:
                await self.update_stream_channels()
                current_channel = self.stream_channels[source.camera_name]
            self.log.debug('Get stream source')
            await current_channel.source_queue.put(source)
            self.responses.task_done()

    async def update_stream_channels(self):
        self.stream_channels.clear()
        active_cameras = await ActiveCameras.get_active_camera_list()
        for camera in active_cameras:
            self.stream_channels[camera[0]] = StreamChannel(camera[0])
        self.log.debug('Channels updated')

    async def run_channel(self, channel):
        if channel.consumer_number == 0:
            if channel.task:
                self.log.debug('Cancelling task')
                channel.task.cancel()
                await channel.task
            channel.consumer_number += 1
            self.log.debug('Sending stream request')
            request = ServerRequest(request_type='stream',
                                    camera_name=channel.camera_name)
            await self.send_request(request)
            self.log.debug('START COURUTINE')
            channel.task = self.loop.create_task(channel.run_channel())
            return
        self.log.debug('COURUTINE ALREADY RUNNING')
        channel.consumer_number += 1


class StreamChannel:

    source_queue = asyncio.Queue()
    consumer_number = 0
    consumer_list = []
    source = None
    task = None
    source_timeout = 1

    def __init__(self, camera_name):
        self.camera_name = camera_name
        self.log = logging.getLogger(self.camera_name)

    async def add_consumer(self, consumer):
        self.log.debug('Get New Consumer')
        self.consumer_list.append(consumer)

    async def run_channel(self):
        try:
            self.source = await asyncio.wait_for(self.source_queue.get(),
                                                 self.source_timeout)
        except TimeoutError:
            self.log.debug('SOURCE TIMEOUT')
            await self.clean_up()
            return

        self.log.debug('Get stream source')
        self.source_queue.task_done()
        try:
            while self.consumer_number > 0 and self.source:
                data = await self.source.reader.read(65536)
                self.log.debug('DATA RECEIVED %s', len(data))
                if not data:
                    self.log.debug('Connection to camera lost')
                    raise asyncio.CancelledError
                await self.send_to_all(data)

        except asyncio.CancelledError:
            self.log.debug('Courutine cancelled')
        finally:
            await self.clean_up()

    async def send_to_all(self, data):
        for consumer in self.consumer_list:
            try:
                consumer.writer.write(data)
                await consumer.writer.drain()
                self.log.debug('DATA SENDED %s', len(data))
            except Exception as error:
                self.log.debug('Connection to consumer lost: %s',
                               error)
                self.consumer_list.remove(consumer)
                self.consumer_number -= 1
#               consumer.writer.close()
#               await consumer.writer.wait_closed() ?????????????

    async def clean_up(self):
        if self.source:
            self.log.debug('CLOSING SOURCE CONNECTION')
            self.source.writer.close()
            await self.source.writer.wait_closed()
            self.log.debug('SOURCE CONNECTION CLOSED')
        self.log.debug('PROCESS CONSUMERS')

        if self.consumer_list:
            for consumer in self.consumer_list:
                self.log.debug('CLOSING CONNECTION TO CONSUMER %s',
                               consumer.writer.get_extra_info('peername'))
                consumer.writer.close()
                await consumer.writer.wait_closed()
                self.consumer_list.remove(consumer)
                self.log.debug('CLOSE CONNECTION TO CONSUMER %s',
                               self.consumer_number)
        self.consumer_number = 0
        self.source = None
        self.task = None
        self.log.debug('COURUTINE ENDED')


class VideoRequestManager(BaseManager, metaclass=SingletonMeta):

    log = logging.getLogger('Video Request Manager')
    requested_videos = {}

    async def run_manager(self):
        await super().run_manager()
        self.loop.create_task(self.garb_collector())

    async def process_requesters(self):
        while True:
            self.log.debug('Waiting for video request')
            try:
                requester = await self.requesters.get()
            except asyncio.CancelledError:
                break

            self.requesters.task_done()
            self.log.info('get video requester %s', requester.video_name)
            try:
                current_request = self.requested_videos[requester.video_name]
            except KeyError:
                request = VideoRequest(self.signal, requester.video_name)
                self.requested_videos[requester.video_name] = request
                current_request = self.requested_videos[requester.video_name]
                self.loop.create_task(current_request.process_request())
                self.log.debug('Created video request')
            else:
                self.log.debug('Video request alredy created')
            finally:
                current_request.add_requester(requester)

    async def process_responses(self):
        while True:
            self.log.debug('Waiting for video response')
            try:
                response = await self.responses.get()
            except asyncio.CancelledError:
                break

            try:
                current_response = self.requested_videos[response.video_name]
            except KeyError:
                self.log.debug('No such request %s', response.video_name)
            else:
                self.log.info('KEYS: %s', self.requested_videos.keys())
                await current_response.response_queue.put(response)

            self.responses.task_done()

    async def garb_collector(self):
        await asyncio.sleep(10)
        for request in self.requested_videos.keys():
            if self.requested_videos[request].task_done:
                del self.requested_videos[request]


class VideoRequest:

    task_done = False
    response_queue = asyncio.Queue()
    response = None
    requesters = []
    response_timeout = 5

    def __init__(self, signal_handler, video_name):
        self.signal = signal_handler
        self.video_name = video_name
        self.log = logging.getLogger(self.video_name)

    async def send_request(self, request):
        await self.signal.signal_queue.put(request)

    async def add_requester(self, requester):
        self.requesters.append(requester)

    async def process_request(self):
        request = ServerRequest(request_type='video',
                                video_name=self.video_name)
        await self.send_request(request)
        try:
            self.response = await asyncio.wait_for(self.response_queue.get(),
                                                   self.response_timeout)
        except TimeoutError:
            self.log.debug('Response TIMEOUT')
            self.response = 'failure'

        for requester in self.requesters:
            requester.writer.write(self.response.request_result.encode())
            requester.writer.close()
            await requester.writer.wait_closed()
            self.log.info('RESPONSE NAME: %s', self.response.video_name)

        self.task_done = True


class SignalManager(BaseManager):

    pass