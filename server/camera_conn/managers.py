import asyncio
import logging
from camera_utils import ServerRequest, SingletonMeta
from db import ActiveCameras


class BaseManager:

    responses = asyncio.Queue()
    requesters = asyncio.Queue()
    loop = asyncio.get_event_loop()

    async def run_manager(self):
        self.log.info('Starting manager')
        loop = asyncio.get_running_loop()
        loop.create_task(self.process_requesters())
        loop.create_task(self.process_responses())

    async def process_requesters(self):
        raise NotImplementedError

    async def process_responses(self):
        raise NotImplementedError


class VideoStreamManager(BaseManager, metaclass=SingletonMeta):

    def __init__(self, signal_handler):
        self.signal = signal_handler

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
            try:
                await current_channel.consumers_queue.put(requester)
            except asyncio.CancelledError:
                break

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
            try:
                await current_channel.source_queue.put(source)
            except asyncio.CancelledError:
                break

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
            await self.send_stream_request(request)
            self.log.debug('START COURUTINE')
            channel.task = self.loop.create_task(channel.run_channel())
            return
        self.log.debug('COURUTINE ALREADY RUNNING')
        channel.consumer_number += 1

    async def send_stream_request(self, request):
        await self.signal.signal_queue.put(request)


class StreamChannel:

    consumers_queue = asyncio.Queue()
    source_queue = asyncio.Queue()
    consumer_number = 0
    consumer_list = []
    source = None
    task = None
    source_timeout = 1

    def __init__(self, camera_name):
        self.camera_name = camera_name
        self.log = logging.getLogger(self.camera_name)

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
                while self.consumers_queue.qsize() > 0:
                    self.log.info('Get new consumer')
                    self.consumer_list.append(await self.consumers_queue.get())
                    self.consumers_queue.task_done()
                    self.log.debug('Consumer added to list')

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

        while self.consumers_queue.qsize() > 0:
            self.log.debug('Getting consumers')
            self.consumer_list.append(await self.consumers_queue.get())
            self.consumers_queue.task_done()
            self.log.debug('Consumers flushed %s', self.consumer_list)

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

    async def process_requesters(self):
        log = logging.getLogger('Video Manager')
        log.info('Thread started')
#       video_requesters = {}
        self.run_video_manager()
        """
        while self.video_manager_running():
            while self.video_requesters_queue.qsize() > 0:
                requester = self.video_requesters_queue.get()
                log.info('get video requester %s', requester.video_name)
                if requester.video_name in video_requesters:
                    video_requesters[requester.video_name].append(requester)
                else:
                    video_request_time =
                    datetime.datetime.now(tz=self.timezone)
                    log.info('VIDEO NAME:%s', requester.video_name)
                    video_requesters[requester.video_name] =
                    [video_request_time, requester]
                    log.info('put video request to queue')
                    self.signal_queue.put(ServerRequest(request_type='video',
                                                        video_name=requester.video_name))

            while self.video_response_queue.qsize() > 0:
                video_response = self.video_response_queue.get()
                log.info('Get video response from queue')

                log.info('KEYS: %s', video_requesters.keys())
                for requester in
                video_requesters[video_response.video_name][1:]:
                    requester.connection.send(video_response.request_result.encode())
                    requester.connection.close()
                    log.info('RESPONSE NAME: %s', video_response.video_name)
                del video_requesters[video_response.video_name]

            if not video_requesters:
                log.info('No more video requesters')
                break

            for item in video_requesters.keys():
                if  (datetime.datetime.now(tz=self.timezone) -
                video_requesters[item][0]).seconds >
                self.video_request_timeout:
                    log.info('Video requester: %s, timeout', item)
                    self.video_response_queue.put(ServerRequest(request_type='video',
                                                                request_result='failure',
                                                                video_name=item))
        """
