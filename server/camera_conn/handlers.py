import asyncio
import logging
import json
import os
from db import CameraRecord, UserRecord
from camera_utils import SingletonMeta, ServerRequest
from managers import VideoStreamManager, VideoRequestManager


class BaseHandler(object):

    DEBUG = False

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
        return True


class NewRecordHandler(BaseHandler):

    log = logging.getLogger('New records')

    @classmethod
    async def handle(self, request):
        if request.request_type != 'new_record':
            return
        if request.db_record:
            method = NewRecordHandler
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
        if request.request_type != 'stream_response':
            return

        self.log.info('Handler started')
        self.log.debug('Put request to stream source queue')
        await self.manager.stream_sources.put(request)
        return True


class VideoResponseHandler(BaseHandler):

    log = logging.getLogger('Video Response')
    manager = VideoRequestManager(SignalHandler)
    video_save_path = ''
    debug_video_save_path = ''

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
            await self.manager.video_response_queue.put(response)
            self.log.error('No such video')
            return True

        try:
            while True:
                data = await request.reader.read(655360)
                video_data += data
                if data == b"" or self.DEBUG:
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
            await self.manager.video_response_queue.put(response)
            self.log.warning('Failed to receive video file')
            return True

        self.log.info('%s', self.debug_video_save_path)
        if self.DEBUG:
            video_name_save = os.path.join(str(self.debug_video_save_path) +
                                           '/' +
                                           request.video_name.split('|')[0] +
                                           '.mp4')
        else:
            video_name_save = os.path.join(str(self.video_save_path) +
                                           request.video_name.split('|')[0] +
                                           '.mp4')

        self.log.info('Saving file')
        async with open(video_name_save, "wb") as video:
            await video.write(video_data)
        response = ServerRequest(request_type='video_reponse',
                                 request_result='success',
                                 video_name=request.video_name)
        await self.manager.video_response_queue.put()
        self.log.info('File received')
        return True


class VideoRequestHandler(BaseHandler):

    log = logging.getLogger('Video Request')
    manager = VideoRequestManager(SignalHandler)

    @classmethod
    async def handle(self, request):
        if request.request_type != 'video_request':
            return

        self.log.debug('Put video request to queue')
        await self.manager.video_requesters_queue.put(request)
        return True


class AproveUserResponseHandler(BaseHandler):

    log = logging.getLogger('Signal handler')

    @classmethod
    async def handle(self, request):
        if request.request_type != 'aprove_user_request':
            return
        log = logging.getLogger('User aprove')
        request.writer.close()
        await request.writer.wait_closed()
        log.info('Updating User:%s', request.username)
        await UserRecord.save(request)
        return True


class AproveUserRequestHandler(BaseHandler):

    log = logging.getLogger('Signal handler')

    @classmethod
    async def handle(self, request):
        if request.request_type != 'aprove_user_response':
            return
        logging.debug('User Request processing %s', request)
        await self.signal_queue.put(request)
        request.connection.close()
        return True
