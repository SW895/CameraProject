import asyncio
import logging
import json
from camera_conn.settings import SOCKET_BUFF_SIZE


class Server:

    handlers = []
    buff_size = SOCKET_BUFF_SIZE

    def __init__(self, sock):
        self.sock = sock
        name = f'Server:{self.sock}'
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
        builder = RequestBuilder().with_args(writer=writer,
                                             reader=reader) \
                                  .with_bytes(data)
        request = builder.build()
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


class ServerRequest:

    writer = None
    reader = None

    def add(self, **kwargs):
        self.client_id = 'main'  # for testing
        self.__dict__.update(kwargs)

    def __eq__(self, other):
        SameObject = isinstance(other, self.__class__)
        if SameObject:
            return True
        if self.__dict__ == other.__dict__:
            return True
        return False

    def __str__(self):
        fields = self.__dict__.copy()
        try:
            del fields['writer']
            del fields['reader']
        except KeyError:
            pass
        return str(fields)

    def serialize(self):
        fields = self.__dict__.copy()
        try:
            del fields['writer']
            del fields['reader']
        except KeyError:
            pass
        serialized = json.dumps(fields) + '\n'
        return serialized


class RequestBuilder:
    args = {}

    def __init__(self):
        self.args = {}
        self.byte_line = None
        self.reset()

    def reset(self):
        self._product = ServerRequest()

    def with_args(self, **kwargs):
        self.args.update(kwargs)
        return self

    def with_bytes(self, byte_line):
        args = json.loads(byte_line.decode())
        self.args.update(args)
        return self

    def build(self):
        self._product.add(**self.args)
        return self._product
