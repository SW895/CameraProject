import asyncio
import logging
from request_builder import RequestBuilder
from settings import SOCKET_BUFF_SIZE
from prometheus_client import (
    Counter,
    Summary,
)


denied_requests_counter = Counter(
    'camera_conn_denied_requests',
    'Number of denied requests',
)
accepted_request_counter = Counter(
    'camera_conn_accepted_requests',
    'Number of accepted requests',
)
request_handle_time = Summary(
    'camera_conn_request_handle_time',
    'Request handle time',
)


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
            self.router,
            sock=self.sock
        )
        async with self.server:
            await self.server.serve_forever()

    @request_handle_time.time()
    async def router(self, reader, writer):
        data = await reader.read(SOCKET_BUFF_SIZE)
        request_handle_time.observe(len(data))
        builder = RequestBuilder() \
            .with_args(writer=writer,
                       reader=reader) \
            .with_bytes(data)
        if builder.validate():
            request = builder.build()
        else:
            self.log.error('Failed to build request')
            return
        #self.log.debug('Request received. Sending reply')
        reply = 'accepted'
        try:
            request.writer.write(reply.encode())
            await request.writer.drain()
        except BrokenPipeError or ConnectionResetError:
            self.log.error('Failed to send reply')
            request.writer.close()
            await request.writer.wait_closed()
        else:
            #self.log.debug('Start handler %s', request.request_type)
            await self.handler(request)

    async def handler(self, request):
        for handler in self.handlers:
            result = await handler.handle(request)
            if result:
                accepted_request_counter.inc()
                break
        else:
            self.log.warning('Wrong request type. Closing connection')
            request.writer.close()
            await request.writer.wait_closed()
            denied_requests_counter.inc()
