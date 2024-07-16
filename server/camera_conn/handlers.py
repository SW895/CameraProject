import asyncio
import logging
import json
from db import CameraRecord
from camera_utils import SingletonMeta
from managers import VideoStreamManager, VideoRequestManager


class BaseHandler(object):

    @classmethod
    async def handle(self, request):
        raise NotImplementedError


class SignalHandler(BaseHandler, metaclass=SingletonMeta):

    signal_queue = asyncio.Queue()
    log = logging.getLogger('Signal handler')

    @classmethod
    async def handle(self, connection):
        if connection.request_type != 'signal':
            return

        self.log.info('Handler started')
        while True:
            self.log.info('Waiting for new signal')
            signal = await self.signal_queue.get()
            self.signal_queue.task_done()
            self.log.info('Get signal:%s', signal.request_type)
            try:
                self.log.info('Sending signal')
                message = signal.serialize() + '\n'
                connection.writer.write(message.encode())
                await connection.writer.drain()
            except Exception as error:
                self.log.warning('Connection lost. Error:%s', error)
                break

        connection.writer.close()
        await connection.writer.wait_closed()


class NewRecordHandler(BaseHandler):

    log = logging.getLogger('New records')

    @classmethod
    async def handle(self, request):
        if request.request_type != 'new_record':
            return
        #if request.db_record:
        #    method = NewRecordHandler
        self.log.debug('Handler started')
        if request.camera_name:
            self.log.debug('Camera record method')
            method = CameraRecord

        result = b""
        data = b""
        self.log.info('Receiving new records')
        while True:
            data = await request.reader.read(100000)
            result += data
            if data == b"":
                break

        self.log.info('New records received')
        request.writer.close()
        await request.writer.wait_closed()

        records = result.decode().split('\n')
        for record in records:
            if record != "":
                self.log.debug('RECORD:%s', record)
                await method.save_queue.put(json.loads(record))
        loop = asyncio.get_running_loop()
        loop.create_task(method.save())
        return True


class VideoStreamRequestHandler(BaseHandler):

    log = logging.getLogger('Video Stream Request handler')
    manager = VideoStreamManager(SignalHandler)

    @classmethod
    async def handle(self, request):
        if request.request_type != 'stream_request':
            return

        self.log.info('Handler started')
        self.log.debug('Put request to stream request queue')
        await self.manager.stream_requesters.put(request)
        return True


class VideoStreamResponseHandler(BaseHandler):

    log = logging.getLogger('Video Stream Source handler')
    manager = VideoStreamManager(SignalHandler)

    @classmethod
    async def handle(self, request):
        if request.request_type != 'stream_source':
            return

        self.log.info('Handler started')
        self.log.debug('Put request to stream source queue')
        await self.manager.stream_sources.put(request)
        return True


class VideoResponseHandler(BaseHandler):

    log = logging.getLogger('Signal handler')

    @classmethod
    async def handle(self, request):
        pass


class VideoRequestHandler(BaseHandler):

    log = logging.getLogger('Signal handler')

    @classmethod
    async def handle(self, request):
        pass


class AproveUserResponse(BaseHandler):

    log = logging.getLogger('Signal handler')

    @classmethod
    async def handle(self, request):
        pass


class AproveUserRequest(BaseHandler):

    log = logging.getLogger('Signal handler')

    @classmethod
    async def handle(self, request):
        pass

