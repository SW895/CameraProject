import asyncio
import logging
from request_builder import RequestBuilder
from settings import SOCKET_BUFF_SIZE


class AsyncServer:

    def __init__(self, sock):
        self.sock = sock
        name = f'Server:{self.sock.getsockname()}'
        self.log = logging.getLogger(name)
        self.handlers = []

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
        data = await reader.read(SOCKET_BUFF_SIZE)
        builder = RequestBuilder().with_args(writer=writer,
                                             reader=reader) \
                                  .with_bytes(data)
        request = builder.build()
        # self.log.info('Request received. Sending reply')
        reply = 'accepted'
        try:
            request.writer.write(reply.encode())
            await request.writer.drain()
        except BrokenPipeError or ConnectionResetError:
            self.log.error('Failed to send reply')
            request.writer.close()
            await request.writer.wait_closed()
        else:
            # self.log.info('Start handler %s', request.request_type)
            for handler in self.handlers:
                result = await handler.handle(request)
                if result:
                    break
            else:
                self.log.warning('Wrong request type. Closing connection')
                request.writer.close()
                await request.writer.wait_closed()
