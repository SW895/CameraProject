import asyncio
import aiofiles
import logging
import json
import os
from settings import (
    SOCKET_BUFF_SIZE,
    GLOBAL_TEST
)
from db import (
    NewVideoRecord,
    CameraRecord,
    UserRecord
)
from request_builder import RequestBuilder
from managers import (
    VideoStreamManager,
    VideoRequestManager,
    SignalCollector
)


class BaseHandler(object):

    @classmethod
    async def handle(self, request):
        if request.request_type not in self.request_type:
            return
        if self.validate(request):
            await self.process_request(request)
            return True

    @classmethod
    def validate(self, request):
        for handler_attribute in self.handler_attributes:
            if handler_attribute not in request.__dict__:
                return False
        return True

    @classmethod
    async def process_request(self, request):
        raise NotImplementedError


class SignalHandler(BaseHandler):

    log = logging.getLogger('Signal handler')
    manager = SignalCollector()
    handler_attributes = ('request_type', )
    request_type = ('signal', )

    @classmethod
    async def process_request(self, request):
        self.log.debug('Signal handler started')
        await self.manager.client_queue.put(request)


class NewRecordHandler(BaseHandler):

    log = logging.getLogger('New records')
    handler_attributes = ('request_type', 'record_size')
    request_type = (
        'new_video_record',
        'new_camera_record',
        'aprove_user_response',
    )

    @classmethod
    def set_method(self, record_handler):
        self._record_handler = record_handler

    @classmethod
    def get_handler(self):
        return self._record_handler

    @classmethod
    async def save(self):
        await self._record_handler.save()

    @classmethod
    async def process_request(self, request):
        if request.request_type == 'new_video_record':
            self.log.debug('New video record method')
            self.set_method(NewVideoRecord(request))
        elif request.request_type == 'new_camera_record':
            self.log.debug('Camera record method')
            self.set_method(CameraRecord(request))
        elif request.request_type == 'aprove_user_response':
            self.log.debug('User record method')
            self.set_method(UserRecord(request))

        result = b""
        data = b""
        self.log.info('Receiving new records')
        while len(result) < request.record_size:
            data = await request.reader.read(SOCKET_BUFF_SIZE)
            result += data
            if data == b"":
                break

        self.log.info('New records received')
        records = result.decode().split('\n')
        for record in records:
            if record:
                self.log.debug('RECORD:%s', record)
                await self.get_handler().save_queue.put(json.loads(record))
        await self.save()


class VideoStreamRequestHandler(BaseHandler):

    log = logging.getLogger('Video Stream Request handler')
    manager = VideoStreamManager()
    handler_attributes = ('request_type', 'camera_name')
    request_type = ('stream_request', )

    @classmethod
    async def process_request(self, request):
        self.log.info('Handler started')
        self.log.debug('Put request to stream request queue')
        await self.manager.requesters.put(request)


class VideoStreamResponseHandler(BaseHandler):

    log = logging.getLogger('Video Stream Source handler')
    manager = VideoStreamManager()
    handler_attributes = ('request_type', 'camera_name')
    request_type = ('stream_response', )

    @classmethod
    async def process_request(self, request):
        self.log.info('Handler started')
        self.log.debug('Put request to stream source queue')
        await self.manager.responses.put(request)


class VideoRequestHandler(BaseHandler):

    log = logging.getLogger('Video Request')
    manager = VideoRequestManager()
    handler_attributes = ('request_type', 'video_name')
    request_type = ('video_request', )

    @classmethod
    async def process_request(self, request):
        self.log.debug('Put video request to queue')
        await self.manager.requesters.put(request)


class VideoResponseHandler(BaseHandler):

    log = logging.getLogger('Video Response')
    manager = VideoRequestManager()
    video_save_path = '/home/app/web/mediafiles/'
    handler_attributes = (
        'request_type',
        'video_size',
        'video_name',
    )
    request_type = ('video_response', )

    @classmethod
    async def save_file(self, name, data):
        if GLOBAL_TEST:
            return
        async with aiofiles.open(name, mode="wb") as video:
            await video.write(data)

    @classmethod
    async def process_request(self, request):
        if request.request_type != 'video_response':
            return

        self.log.info('Courutine started')
        video_data = b""
        data = b""

        if request.video_size == 0:
            builder = RequestBuilder().with_args(
                request_type='video_reponse',
                request_result='failure',
                video_name=request.video_name
            )
            response = builder.build()
            await self.manager.responses.put(response)
            self.log.error('No such video')

        try:
            while len(video_data) < request.video_size:
                data = await request.reader.read(SOCKET_BUFF_SIZE)
                video_data += data
                if data == b"":
                    break
        except asyncio.CancelledError:
            pass
        finally:
            request.writer.close()
            await request.writer.wait_closed()

        if len(video_data) != request.video_size:
            builder = RequestBuilder().with_args(
                request_type='video_reponse',
                request_result='failure',
                video_name=request.video_name
            )
            response = builder.build()
            await self.manager.responses.put(response)
            self.log.warning('Failed to receive video file')

        self.log.info('%s', self.video_save_path)
        video_name_save = os.path.join(
            str(self.video_save_path)
            + request.video_name.split('|')[0]
            + '.mp4'
        )

        self.log.info('Saving file %s', video_name_save)
        await self.save_file(video_name_save, video_data)
        builder = RequestBuilder().with_args(
            request_type='video_reponse',
            request_result='success',
            video_name=request.video_name
        )
        response = builder.build()
        await self.manager.responses.put(response)
        self.log.info('File received')


class AproveUserRequestHandler(BaseHandler):

    log = logging.getLogger('Aprove User Request Handler')
    signal = SignalCollector()
    handler_attributes = ('request_type', )
    request_type = ('aprove_user_request', )

    @classmethod
    async def process_request(self, request):
        self.log.debug('User Request processing %s', request)
        await self.signal.signal_queue.put(request)
        request.writer.close()
        await request.writer.wait_closed()
