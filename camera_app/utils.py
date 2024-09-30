import asyncio
import threading
from request_builder import RequestBuilder
from settings import (
    SOCKET_BUFF_SIZE,
    SERVER_HOST,
    SERVER_PORT,
    GET_SERVER_EVENTS_TIMEOUT,
)


class Singleton(type):

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class ConnectionMixin:

    buff_size = SOCKET_BUFF_SIZE
    host = SERVER_HOST
    port = SERVER_PORT
    connection_timeout = GET_SERVER_EVENTS_TIMEOUT
    background_tasks = set()

    async def connect_to_server(self, request):
        try:
            reader, writer = await asyncio.open_connection(
                self.host, self.port)
        except ConnectionRefusedError:
            return None, None

        try:
            writer.write(request.serialize().encode())
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            return None, None

        reply = await reader.read(self.buff_size)
        if reply.decode() == 'accepted':
            return reader, writer
        return None, None

    async def send_records(self, request, records):
        reader, writer = await self.connect_to_server(request)
        if writer:
            try:
                writer.write(records.encode())
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                self.log.error('Connection Error')
            else:
                reply = await reader.read(self.buff_size)
                if reply:
                    builder = RequestBuilder().with_bytes(reply)
                    response = builder.build()
                    if response.status == 'success':
                        return True
                writer.close()
                await writer.wait_closed()
        return False


class ErrorAfter(object):
    '''
    Callable that will raise `CallableExhausted`
    exception after `limit` calls
    '''
    def __init__(self, limit, return_value):
        self.limit = limit
        self.calls = 0
        self.return_value = return_value

    def __call__(self, *args):
        self.calls += 1
        if self.calls > self.limit:
            raise CallableExhausted
        return self.return_value


class CallableExhausted(Exception):
    pass


def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function,
                                  args=args,
                                  kwargs=kwargs)
        thread.start()
        return thread

    return inner
