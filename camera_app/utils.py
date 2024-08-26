import logging
import asyncio
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
            logging.error('Failed to connect to server')
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
