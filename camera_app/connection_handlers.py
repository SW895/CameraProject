import logging
import json
import smtplib
import ssl
import os
import aiofiles
from streaming import VideoStreamManager
from request_builder import RequestBuilder
from utils import ConnectionMixin
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from settings import (
    APROVED_USER_LIST,
    APROVE_ALL,
    EMAIL_ENABLED,
    EMAIL_BACKEND,
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_USER,
    SAVE_PATH,
)


class BaseClientHandler(ConnectionMixin):

    async def handle(self, request, loop):
        if request.request_type != self.request_type:
            return False
        task = loop.create_task(self.process_request(request))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return True

    async def process_request(self, request):
        raise NotImplementedError


class AproveUserHandler(BaseClientHandler):

    request_type = 'aprove_user_request'
    log = logging.getLogger('Aprove user request handler')

    async def process_request(self, request):
        self.log.info('Handler started')
        username = request.username
        email = request.email

        if (username in APROVED_USER_LIST) or APROVE_ALL:
            record = {'username': username, 'request_result': 'aproved'}
            self.log.info('%s aproved', username)
            result = True
        else:
            record = {'username': username, 'request_result': 'denied'}
            self.log.info('%s denied', username)
            result = False

        builder = RequestBuilder().with_args(
            request_type='aprove_user_response',
            record_size=len(record))
        request = builder.build()
        reader, writer = await self.connect_to_server(request)
        serialized_record = json.dumps(record) + '\n'
        if writer:
            try:
                writer.write(serialized_record.encode())
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                self.log.error('Connection Error')
            else:
                reply = await reader.read(self.buff_size)
                response = json.loads(reply.decode())
                if response['status'] == 'success':
                    if EMAIL_ENABLED:
                        self.send_email(username, email, result)
                writer.close()
                await writer.wait_closed()

    # TODO MAKE ASYNC
    def send_email(self, username, email, result):
        message = MIMEMultipart('alternative')

        message['From'] = EMAIL_USER
        message['To'] = email

        if result:
            message['Subject'] = 'Account approved'
            text = f"""\
            Hi {username}. \
            Your account has been successfully aproved by admin, \
            now you can login with your username and password.
            """
            html = f"""\
            <html>
            <body>
                <p>
                Hi {username}. \
                Your account has been successfully aproved by admin, \
                now you can login with your username and password.
                </p>
            </body>
            </html>
            """
        else:
            message['Subject'] = 'Account denied'
            text = f"""\
            Hi {username}. Your account has been denied by admin.
            """
            html = f"""\
            <html>
            <body>
                <p>
                Hi {username}. Your account has been denied by admin.
                </p>
            </body>
            </html>
            """

        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        message.attach(part1)
        message.attach(part2)
        context = ssl.create_default_context()

        with smtplib.SMTP(EMAIL_BACKEND, EMAIL_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, email, message.as_string())


class VideoRequestHandler(BaseClientHandler):

    request_type = 'video_request'
    log = logging.getLogger('Handler video request')

    async def process_request(self, request):
        self.log.info('Handler started')
        video_bytes = b""
        video_name = request.video_name.split('|')[0]
        camera_name = request.video_name.split('|')[1]
        self.log.debug('Video name:%s, Camera name: %s',
                       video_name,
                       camera_name)
        full_video_name = SAVE_PATH / (camera_name
                                       + '/'
                                       + video_name.split('T')[0]
                                       + '/'
                                       + video_name
                                       + '.mp4')
        self.log.debug('Full video name^ %s', full_video_name)

        if os.path.exists(full_video_name):
            async with aiofiles.open(full_video_name, mode="rb") as video:
                video_bytes = await video.read()
                self.log.debug('video length: %s', len(video_bytes))
            builder = RequestBuilder().with_args(
                request_type='video_response',
                video_name=request.video_name,
                video_size=len(video_bytes))
        else:
            builder = RequestBuilder().with_args(
                request_type='video_response',
                video_name=request.video_name,
                video_size=0)
            self.log.error('No such video %s', full_video_name)

        request = builder.build()
        _, writer = await self.connect_to_server(request)
        if writer and video_bytes:
            try:
                writer.write(video_bytes)
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                self.log.error('Connection error')
            else:
                writer.close()
                await writer.wait_closed()
        self.log.info('Handler ended')


class StreamHandler(BaseClientHandler):

    request_type = 'stream_request'
    manager = VideoStreamManager()

    async def process_request(self, request):
        await self.manager.requesters.put(request)
