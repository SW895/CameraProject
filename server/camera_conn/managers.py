import asyncio
import logging
from camera_utils import SingletonMeta
from request_builder import RequestBuilder
from settings import (SOCKET_BUFF_SIZE,
                      STREAM_SOURCE_TIMEOUT,
                      VIDEO_REQUEST_TIMEOUT,
                      GARB_COLLECTOR_TIMEOUT)


class BaseManager:

    background_tasks = set()

    def set_signal_handler(self, signal_handler):
        self._signal_hander = signal_handler

    async def run_manager(self):
        self.log.info('Starting manager')
        self.loop = asyncio.get_running_loop()
        self.background_tasks.add(
            self.loop.create_task(self.process_requesters()))
        self.background_tasks.add(
            self.loop.create_task(self.process_responses()))
        self.background_tasks.add(
            self.loop.create_task(self.garb_collector()))
        for task in self.background_tasks:
            task.add_done_callback(self.background_tasks.discard)

    async def process_requesters(self):
        raise NotImplementedError

    async def process_responses(self):
        raise NotImplementedError

    async def send_request(self, signal):
        await self._signal_hander.signal_queue.put(signal)

    async def garb_collector(self):
        pass


class VideoStreamManager(BaseManager, metaclass=SingletonMeta):

    responses = asyncio.Queue()
    requesters = asyncio.Queue()
    stream_channels = {}
    log = logging.getLogger('VideoStream Manager')

    async def process_requesters(self):
        while True:
            self.log.debug('Waiting for stream requester')
            try:
                requester = await self.requesters.get()
            except asyncio.CancelledError:
                break
            self.requesters.task_done()
            try:
                current_channel = self.stream_channels[requester.camera_name]
            except KeyError:
                await self.update_stream_channels()
            try:
                current_channel = self.stream_channels[requester.camera_name]
            except KeyError:
                self.log.error('No such camera')
                continue
            self.log.debug('Starting channel')
            await self.run_channel(current_channel, requester)

    async def process_responses(self):
        while True:
            self.log.debug('Waiting for a stream source')
            try:
                source = await self.responses.get()
            except asyncio.CancelledError:
                break
            self.responses.task_done()
            try:
                current_channel = self.stream_channels[source.camera_name]
            except KeyError:
                self.log.error('No such channel')
                continue
            self.log.debug('Get stream source')
            await current_channel.source_queue.put(source)

    async def update_stream_channels(self):
        self.stream_channels.clear()
        active_cameras = await self.get_active_camera_list()
        for camera in active_cameras:
            self.stream_channels[camera[0]] = StreamChannel(camera[0])
        self.log.debug('Channels updated')

    def set_camera_list_updater(self, camera_handler):
        self._camera_handler = camera_handler

    async def get_active_camera_list(self):
        return await self._camera_handler.get_active_camera_list()

    async def run_channel(self, channel, requester):
        if channel.consumer_list:
            self.log.debug('COURUTINE ALREADY RUNNING')
        else:
            if channel.task:
                self.log.debug('Cancelling task')
                channel.task.cancel()
                await channel.task
            self.log.debug('Sending stream request')
            builder = RequestBuilder().with_args(
                request_type='stream_request',
                camera_name=channel.camera_name)
            request = builder.build()
            await self.send_request(request)
            self.log.debug('START COURUTINE')
            channel.task = self.loop.create_task(channel.run_channel())
        await channel.add_consumer(requester)


class StreamChannel:

    def __init__(self, camera_name):
        self.camera_name = camera_name
        self.log = logging.getLogger(self.camera_name)
        self.source_queue = asyncio.Queue()
        self.consumer_list = []
        self.source = None
        self.task = None

    def __eq__(self, other):
        SameObject = isinstance(other, self.__class__)
        if SameObject:
            return True
        if self.camera_name == other.camera_name:
            return True
        return False

    async def add_consumer(self, consumer):
        self.log.debug('Get New Consumer')
        self.consumer_list.append(consumer)

    async def run_channel(self):
        self.log.debug('CHANNEL STARTED')
        try:
            self.source = await asyncio.wait_for(self.source_queue.get(),
                                                 STREAM_SOURCE_TIMEOUT)
        except TimeoutError:
            self.log.debug('SOURCE TIMEOUT')
            await self.clean_up()
            return 'TimeoutError'
        self.source_queue.task_done()
        try:
            while self.consumer_list and self.source:
                data = await self.source.reader.read(SOCKET_BUFF_SIZE)
                if not data:
                    self.log.debug('Connection to camera lost')
                    raise asyncio.CancelledError
                await self.send_to_all(data)

        except asyncio.CancelledError:
            self.log.debug('Courutine cancelled')
        finally:
            await self.clean_up()
            return True

    async def send_to_all(self, data):
        for consumer in self.consumer_list:
            try:
                consumer.writer.write(data)
                await consumer.writer.drain()
            except Exception as error:
                self.log.debug('Connection to consumer lost: %s', error)
                self.consumer_list.remove(consumer)

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
                self.log.debug('CLOSE CONNECTION TO CONSUMER')
        self.source = None
        self.task = None
        self.log.debug('COURUTINE ENDED')


class VideoRequestManager(BaseManager, metaclass=SingletonMeta):

    responses = asyncio.Queue()
    requesters = asyncio.Queue()
    log = logging.getLogger('Video Request Manager')
    requested_videos = {}

    async def process_requesters(self):
        while True:
            self.log.debug('Waiting for video request')
            try:
                requester = await self.requesters.get()
                self.requesters.task_done()
            except asyncio.CancelledError:
                return

            self.log.info('get video requester %s', requester.video_name)
            try:
                current_request = self.requested_videos[requester.video_name]
            except KeyError:
                current_request = await self.create_new_request(
                    requester.video_name)
            else:
                self.log.debug('Video request alredy created')
            self.log.debug('Add requester to list')
            await current_request.add_requester(requester)

    async def create_new_request(self, video_name):
        self.requested_videos[video_name] = VideoRequest(video_name)
        current_request = self.requested_videos[video_name]
        current_request.task = self.loop.create_task(
            current_request.process_request())
        self.log.debug('Created video request')
        builder = RequestBuilder().with_args(request_type='video_request',
                                             video_name=video_name)
        request = builder.build()
        await self.send_request(request)
        return current_request

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
        while True:
            try:
                await asyncio.sleep(GARB_COLLECTOR_TIMEOUT)
                task_done_list = []
                for request in self.requested_videos:
                    if self.requested_videos[request].task_done:
                        task_done_list.append(request)
                for request in task_done_list:
                    del self.requested_videos[request]
            except asyncio.CancelledError:
                break


class VideoRequest:

    def __init__(self, video_name):
        self.video_name = video_name
        self.log = logging.getLogger(self.video_name)
        self.task_done = False
        self.task = None
        self.response_queue = asyncio.Queue()
        self.response = None
        self.requesters = []

    def __eq__(self, other):
        SameObject = isinstance(other, self.__class__)
        if SameObject:
            return True
        if self.video_name == other.video_name:
            return True
        return False

    async def add_requester(self, requester):
        self.log.debug('Requester added')
        self.requesters.append(requester)

    async def process_request(self):
        try:
            response = await asyncio.wait_for(self.response_queue.get(),
                                              VIDEO_REQUEST_TIMEOUT)
        except TimeoutError:
            self.log.debug('Response TIMEOUT')
            self.response = 'timeout_error'
        else:
            self.response = response.request_result
            self.log.debug('GET RESPONSE')

        for requester in self.requesters:
            requester.writer.write(self.response.encode())
            requester.writer.close()
            await requester.writer.wait_closed()
            self.log.info('RESPONSE NAME: %s', self.response)

        self.task_done = True
        self.task = None
        self.requesters = []


class SignalCollector(BaseManager, metaclass=SingletonMeta):

    signal_queue = asyncio.Queue()
    client_queue = asyncio.Queue()
    log = logging.getLogger('Signal manager')
    clients = {}
    garb_collector_timeout = GARB_COLLECTOR_TIMEOUT

    async def process_requesters(self):  # register clients
        self.clients['main'] = Client('main')
        while True:
            try:
                client = await self.client_queue.get()
            except asyncio.CancelledError:
                break

            if not (client.client_id in self.clients):
                self.log.debug('Client does not exist: %s', client.client_id)
                continue
            else:
                self.clients[client.client_id].update_connection(client)
                self.log.debug('Client exists')
            self.clients[client.client_id].task = self.loop.create_task(
                self.clients[client.client_id].handle_signals())

    async def process_responses(self):  # get signals to transmit
        while True:
            self.log.debug('Wait for signal')
            try:
                signal = await self.signal_queue.get()
            except asyncio.CancelledError:
                break
            self.log.debug('Get signal, processing...')
            try:
                current_client = self.clients[signal.client_id]
            except KeyError:
                self.log.error('No such client %s', signal.client_id)
            else:
                self.log.debug('Put signal to client %s', signal.client_id)
                await current_client.signal_queue.put(signal)


class Client:

    def __init__(self, client_id):
        self.client_id = client_id
        self.log = logging.getLogger(self.client_id)
        self.signal_queue = asyncio.Queue()
        self.dead = False
        self.task = None

    def __eq__(self, other):
        SameObject = isinstance(other, self.__class__)
        if SameObject:
            return True
        if self.client_id == other.client_id:
            return True
        return False

    def update_connection(self, client):
        self.writer = client.writer
        self.reader = client.reader

    async def handle_signals(self):
        while self.signal_queue.qsize() > 0:
            self.log.info('Gets signal from queue')
            try:
                signal = await self.signal_queue.get()
            except asyncio.CancelledError:
                self.log.debug('Courutine cancelled')
                break
            self.signal_queue.task_done()
            self.log.info('Sending signal')
            try:
                self.writer.write(signal.serialize().encode())
                await self.writer.drain()
            except Exception as error:
                self.log.error('Connection to client lost, %s', error)
                break

        self.log.info('No more new events')
        self.writer.close()
        await self.writer.wait_closed()
        self.log.debug('Session ended')
        self.task = None
