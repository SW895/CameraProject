import asyncio
import logging
import json
import os
from .db import NewVideoRecord, CameraRecord, UserRecord
from .camera_utils import SingletonMeta, ServerRequest
from .managers import VideoStreamManager, VideoRequestManager


class BaseHandler(object):

    @classmethod
    async def handle(self, request):
        raise NotImplementedError


class SignalHandler(BaseHandler, metaclass=SingletonMeta):

    signal_queue = asyncio.Queue()
    log = logging.getLogger('Signal handler')
    connection = None

    @classmethod
    async def handle(self, connection):
        if connection.request_type != 'signal':
            return
        self.connection = connection
        self.log.info('Handler started')
        self.log.info('%s', self.connection.writer)
        while True:
            try:
                await self.process_signals()
            except Exception as error:
                self.log.warning('Connection lost. Error:%s', error)
                break

        self.connection.writer.close()
        await self.connection.writer.wait_closed()
        return True

    @classmethod
    async def process_signals(self):
        self.log.info('Waiting for new signal')
        signal = await self.signal_queue.get()
        self.signal_queue.task_done()
        self.log.info('Get signal:%s', signal.request_type)
        self.log.info('Sending signal')
        message = signal.serialize() + '\n'
        self.connection.writer.write(message.encode())
        await self.connection.writer.drain()


class NewRecordHandler(BaseHandler):

    log = logging.getLogger('New records')

    @classmethod
    def set_method(self, record_handler):
        self._record_handler = record_handler

    @property
    def record_handler(self):
        return self._record_handler

    @classmethod
    def save(self):
        loop = asyncio.get_running_loop()
        loop.create_task(self._record_handler.save())

    @classmethod
    async def handle(self, request):
        if request.request_type != 'new_record':
            return
        self.log.debug('Handler started')
        if request.db_record:
            self.log.debug('New video record method')
            self.set_method(NewVideoRecord)
        if request.camera_name:
            self.log.debug('Camera record method')
            self.set_method(CameraRecord)

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
                await self.record_handler.save_queue.put(json.loads(record))
        self.save()
        return True


class VideoStreamRequestHandler(BaseHandler):

    log = logging.getLogger('Video Stream Request handler')
    manager = VideoStreamManager()

    @classmethod
    async def handle(self, request):
        if request.request_type != 'stream_request':
            return

        self.log.info('Handler started')
        self.log.debug('Put request to stream request queue')
        await self.manager.requesters.put(request)
        return True


class VideoStreamResponseHandler(BaseHandler):

    log = logging.getLogger('Video Stream Source handler')
    manager = VideoStreamManager()

    @classmethod
    async def handle(self, request):
        if request.request_type != 'stream_response':
            return

        self.log.info('Handler started')
        self.log.debug('Put request to stream source queue')
        await self.manager.responses.put(request)
        return True


class VideoRequestHandler(BaseHandler):

    log = logging.getLogger('Video Request')
    manager = VideoRequestManager()

    @classmethod
    async def handle(self, request):
        if request.request_type != 'video_request':
            return

        self.log.debug('Put video request to queue')
        await self.manager.requesters.put(request)
        return True


class VideoResponseHandler(BaseHandler):

    log = logging.getLogger('Video Response')
    manager = VideoRequestManager()
    video_save_path = ''

    def save_file(name, data):
        with open(name, "wb") as video:
            video.write(data)

    @classmethod
    async def handle(self, request):
        if request.request_type != 'video_response':
            return

        self.log.info('Courutine started')
        video_data = b""
        data = b""

        if request.video_size == 0:
            response = ServerRequest(request_type='video_reponse',
                                     request_result='failure',
                                     video_name=request.video_name)
            await self.manager.responses.put(response)
            self.log.error('No such video')
            return True

        try:
            while len(video_data) < request.video_size:
                data = await request.reader.read(65536)
                video_data += data
                if data == b"":
                    break
        except asyncio.CancelledError:
            pass
        finally:
            request.writer.close()
            await request.writer.wait_closed()

        if len(video_data) != request.video_size:
            response = ServerRequest(request_type='video_reponse',
                                     request_result='failure',
                                     video_name=request.video_name)
            await self.manager.responses.put(response)
            self.log.warning('Failed to receive video file')
            return True

        self.log.info('%s', self.video_save_path)
        video_name_save = os.path.join(str(self.video_save_path) +
                                       request.video_name.split('|')[0] +
                                       '.mp4')

        self.log.info('Saving file')
        save_coro = asyncio.to_thread(self.save_file,
                                      video_name_save,
                                      video_data)
        await save_coro
        response = ServerRequest(request_type='video_reponse',
                                 request_result='success',
                                 video_name=request.video_name)
        await self.manager.responses.put(response)
        self.log.info('File received')
        return True


class AproveUserRequestHandler(BaseHandler):

    log = logging.getLogger('Aprove User Request Handler')
    signal = SignalHandler

    @classmethod
    async def handle(self, request):
        if request.request_type != 'aprove_user_request':
            return
        self.log.debug('User Request processing %s', request)
        await self.signal.signal_queue.put(request)
        request.writer.close()
        await request.writer.wait_closed()
        return True


class AproveUserResponseHandler(BaseHandler):

    log = logging.getLogger('Aprove User Response')
    record_handler = UserRecord

    @classmethod
    async def handle(self, request):
        if request.request_type != 'aprove_user_response':
            return
        request.writer.close()
        await request.writer.wait_closed()
        self.log.info('Updating User:%s', request.username)
        await self.record_handler.save(request)
        return True
