import asyncio
import logging
from camera_utils import ServerRequest, SingletonMeta, connect_to_db


class VideoStreamManager(metaclass=SingletonMeta):
    
    def __init__(self, signal_handler):
        self.signal = signal_handler
    
    stream_sources = asyncio.Queue()
    stream_requesters = asyncio.Queue()
    stream_channels = {}
    log = logging.getLogger('VideoStream Manager')
    loop = asyncio.get_event_loop()

    async def run_manager(self):
        self.log.info('Starting manager')
        loop = asyncio.get_running_loop()
        loop.create_task(self.process_requesters())
        loop.create_task(self.process_sources())

    async def process_requesters(self):
        while True:
            self.log.debug('Waiting for stream requester')
            try:
                requester = await self.stream_requesters.get()
            except asyncio.CancelledError:
                break

            self.log.debug('Get stream requester')
            try:
                await self.stream_channels[requester.camera_name].consumers_queue.put(requester)
            except KeyError:
                self.log.debug('No such channel. Updating channels')
                await self.update_stream_channels()
                try:
                    await self.stream_channels[requester.camera_name].consumers_queue.put(requester)
                except:
                    self.log.debug('Channel and camera does not exist')
            except asyncio.CancelledError:
                break
            
            self.stream_requesters.task_done()
            self.log.debug('Starting channel')
            self.loop.create_task(self.run_channel(self.stream_channels[requester.camera_name]))

    async def process_sources(self):
        while True:
            self.log.debug('Waiting for a stream source')
            try:
                source = await self.stream_sources.get()
            except asyncio.CancelledError:
                break
            self.log.debug('Get stream source')
            try:
                await self.stream_channels[source.camera_name].source_queue.put(source)
            except KeyError:
                self.log.debug('No such channel. Updating channels')
                await self.update_stream_channels()
                try:
                    await self.stream_channels[source.camera_name].source_queue.put(source)
                except:
                    self.log.debug('Channel and camera does not exist')
            except asyncio.CancelledError:
                break
            
            self.stream_sources.task_done()

    async def update_stream_channels(self):
        self.stream_channels.clear()
        self.log.debug('connecting to db')
        db_conn, cur = connect_to_db(False) #make async
        if db_conn:
            self.log.info('Successfully connected to db')
            cur.execute("SELECT camera_name FROM main_camera WHERE is_active=True")
            active_cameras = cur.fetchall()
            for camera in active_cameras:
                self.stream_channels[camera[0]] = StreamChannel(camera[0])
            cur.close()
            db_conn.close()

    async def run_channel(self, channel):
        if channel.consumer_number == 0:
            if channel.task:
                self.log.debug('Cancelling task')
                channel.task.cancel()
                await channel.task
            channel.consumer_number += 1
            self.log.debug('Sending stream request')
            self.loop.create_task(self.send_stream_request(ServerRequest(request_type='stream', 
                                                                        camera_name=channel.camera_name)))
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
            try:
                self.source = await asyncio.wait_for(self.source_queue.get(), 
                                                    self.source_timeout)
            except TimeoutError:
                self.log.debug('SOURCE TIMEOUT')
                raise asyncio.CancelledError
            self.log.debug('Get stream source')
            self.source_queue.task_done()

            while self.consumer_number > 0 and self.source:            
                while self.consumers_queue.qsize() > 0:
                    self.log.info('Get new consumer')
                    self.consumer_list.append(await self.consumers_queue.get())
                    self.consumers_queue.task_done()
                    self.log.debug('Consumer added to list')

                if self.consumer_list:
                    data = await self.source.reader.read(65536)
                    self.log.debug('DATA RECEIVED %s', len(data))
                    if not data:
                        self.log.debug('Connection to camera lost')
                        raise asyncio.CancelledError
                    for consumer in self.consumer_list:
                        try:
                            consumer.writer.write(data)
                            await consumer.writer.drain()
                            self.log.debug('DATA SENDED %s', len(data))
                        except Exception as error:
                            self.log.debug('Connection to consumer %s lost: %s', 
                                           consumer.writer.get_extra_info('peername'), error)
                            self.consumer_list.remove(consumer)
                            self.log.debug('AAAAAAAAAA:%s', self.consumer_list)
                            self.consumer_number -= 1
                            #consumer.writer.close()
                            #await consumer.writer.wait_closed() ?????????????????
                else:
                    self.log.debug('NO CONSUMERS')
                    raise asyncio.CancelledError
        except asyncio.CancelledError:
            self.log.debug('Courutine cancelled')
        finally:
            await self.clean_up()

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
                self.log.debug('CLOSING CONNECTION TO CONSUMER %s', consumer.writer.get_extra_info('peername'))                
                consumer.writer.close()
                await consumer.writer.wait_closed()
                self.consumer_list.remove(consumer)
                self.log.debug('CLOSE CONNECTION TO CONSUMER %s', self.consumer_number)
        self.consumer_number = 0
        self.source = None
        self.task = None
        self.log.debug('COURUTINE ENDED')


class VideoRequestManager:
    pass