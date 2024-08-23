import threading
import logging
import asyncio
from settings import (
    SOCKET_BUFF_SIZE,
    SERVER_HOST,
    SERVER_PORT,
    GET_SERVER_EVENTS_TIMEOUT,
)


def check_thread(target_function):

    def inner(*args, **kwargs):

        thread_running = False

        for th in threading.enumerate():
            if th.name == target_function.__name__:
                thread_running = True
                break

        if not thread_running:
            logging.info('Starting thread %s', target_function.__name__)
            thread = threading.Thread(target=target_function,
                                      args=args,
                                      name=target_function.__name__)
            thread.start()
            return thread
        else:
            logging.warning('Thread %s already running',
                            target_function.__name__)

    return inner


def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function,
                                  args=args,
                                  kwargs=kwargs)
        thread.start()
        return thread

    return inner


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
        reader, writer = await asyncio.open_connection(
            self.host, self.port)
        try:
            writer.write(request.serialize().encode())
            await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            return None, None

        reply = await reader.read(self.buff_size)
        if reply.decode() == 'accepted':
            return reader, writer
        return None, None
