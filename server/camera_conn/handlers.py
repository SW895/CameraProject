import asyncio
import logging
import json
import os
from settings import (SOCKET_BUFF_SIZE,
                      GLOBAL_TEST)
from db import (NewVideoRecord,
                CameraRecord,
                UserRecord)
from cam_server import RequestBuilder
from managers import (VideoStreamManager,
                      VideoRequestManager,
                      SignalCollector)


class BaseHandler(object):

    @classmethod
    async def handle(self, request):
        raise NotImplementedError


class SignalHandler(BaseHandler):

    log = logging.getLogger('Signal handler')
    manager = SignalCollector()

    @classmethod
    async def handle(self, request):
        if request.request_type != 'signal':
            return
        self.log.debug('Signal handler started')
        await self.manager.client_queue.put(request)
        return True


class NewRecordHandler(BaseHandler):

    buff_size = SOCKET_BUFF_SIZE
    log = logging.getLogger('New records')

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
    async def handle(self, request):
        if request.request_type == 'new_video_record':
            self.log.debug('New video record method')
            self.set_method(NewVideoRecord(request))
        elif request.request_type == 'new_camera_record':
            self.log.debug('Camera record method')
            self.set_method(CameraRecord(request))
        elif request.request_type == 'aprove_user_response':
            self.log.debug('User record method')
            self.set_method(UserRecord(request))
        else:
            return

        result = b""
        data = b""
        self.log.info('Receiving new records')
        while len(result) < request.record_size:
            data = await request.reader.read(self.buff_size)
            result += data
            if data == b"":
                break

        self.log.info('New records received')
        records = result.decode().split('\n')
        for record in records:
            if record != "":
                self.log.debug('RECORD:%s', record)
                await self.get_handler().save_queue.put(json.loads(record))
        await self.save()
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
    buff_size = SOCKET_BUFF_SIZE

    def save_file(name, data):
        if GLOBAL_TEST:
            return
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
            builder = RequestBuilder().with_args(
                request_type='video_reponse',
                request_result='failure',
                video_name=request.video_name)
            response = builder.build()
            await self.manager.responses.put(response)
            self.log.error('No such video')
            return True

        try:
            while len(video_data) < request.video_size:
                data = await request.reader.read(self.buff_size)
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
                video_name=request.video_name)
            response = builder.build()
            await self.manager.responses.put(response)
            self.log.warning('Failed to receive video file')
            return True

        self.log.info('%s', self.video_save_path)
        video_name_save = os.path.join(str(self.video_save_path)
                                       + request.video_name.split('|')[0]
                                       + '.mp4')

        self.log.info('Saving file')
        save_coro = asyncio.to_thread(self.save_file,
                                      video_name_save,
                                      video_data)
        await save_coro
        builder = RequestBuilder().with_args(
            request_type='video_reponse',
            request_result='success',
            video_name=request.video_name)
        response = builder.build()
        await self.manager.responses.put(response)
        self.log.info('File received')
        return True


class AproveUserRequestHandler(BaseHandler):

    log = logging.getLogger('Aprove User Request Handler')
    signal = SignalCollector()

    @classmethod
    async def handle(self, request):
        if request.request_type != 'aprove_user_request':
            return
        self.log.debug('User Request processing %s', request)
        self.log.debug(isinstance(self.signal, SignalCollector))
        await self.signal.signal_queue.put(request)
        request.writer.close()
        await request.writer.wait_closed()
        return True
