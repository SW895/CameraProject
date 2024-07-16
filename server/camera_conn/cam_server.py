import asyncio
import logging
import json
from camera_utils import ServerRequest


class Server:

    handlers = []
    buff_size = 4096

    def __init__(self, address, port, sock):
        self.address = address
        self.port = port
        self.sock = sock
        name = f'Server:{self.port}'
        self.log = logging.getLogger(name)

    def add_handler(self, *args):
        for handler in args:
            self.handlers.append(handler)

    async def run_server(self):
        self.log.debug('Starting server')
        self.server = await asyncio.start_server(
            self.router, sock=self.sock
        )
        async with self.server:
            await self.server.serve_forever()

    async def router(self, reader, writer):
        data = await reader.read(self.buff_size)
        message = data.decode()
        self.log.debug('Message received:%s', message)
        request = json.loads(message, object_hook=lambda d: ServerRequest(**d))
        request.writer = writer
        request.reader = reader

        self.log.info('Request type accepted. Sending reply')
        reply = 'accepted'
        try:
            request.writer.write(reply.encode())
            await request.writer.drain()
        except BrokenPipeError or ConnectionResetError:
            self.log.error('Failed to send reply')
            request.writer.close()
            await request.writer.wait_closed()
        else:
            self.log.info('Start handler %s', request.request_type)
            for handler in self.handlers:
                result = await handler.handle(request)
                if result:
                    break
            else:
                self.log.warning('Wrong request type. Closing connection')
                request.writer.close()
                await request.writer.wait_closed()
