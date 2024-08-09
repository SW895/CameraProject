import asyncio
import socket
from cam_server import AsyncServer
from settings import (EXTERNAL_HOST,
                      EXTERNAL_PORT,
                      EXTERNAL_CONN_QUEUE,
                      INTERNAL_HOST,
                      INTERNAL_PORT,
                      INTERNAL_CONN_QUEUE)
from managers import (VideoStreamManager,
                      VideoRequestManager,
                      SignalCollector)
from db import ActiveCameras
from handlers import (VideoStreamRequestHandler,
                      VideoStreamResponseHandler,
                      SignalHandler,
                      NewRecordHandler,
                      VideoRequestHandler,
                      VideoResponseHandler,
                      AproveUserRequestHandler)
import logging
import time


class Server:

    background_tasks = set()

    def __init__(self):
        self.log = logging.getLogger('MAIN SERVER')
        self.external_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.external_sock.setsockopt(socket.SOL_SOCKET,
                                      socket.SO_REUSEADDR,
                                      1)
        self.external_sock.bind((EXTERNAL_HOST, EXTERNAL_PORT))
        self.external_sock.listen(EXTERNAL_CONN_QUEUE)

        self.internal_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.internal_sock.setsockopt(socket.SOL_SOCKET,
                                      socket.SO_REUSEADDR,
                                      1)
        self.internal_sock.bind((INTERNAL_HOST, INTERNAL_PORT))
        self.internal_sock.listen(INTERNAL_CONN_QUEUE)

        self.internal_server = AsyncServer(self.internal_sock)
        self.external_server = AsyncServer(self.external_sock)
        self.internal_server.add_handler(VideoStreamRequestHandler,
                                         VideoRequestHandler,
                                         AproveUserRequestHandler)
        self.external_server.add_handler(VideoStreamResponseHandler,
                                         VideoResponseHandler,
                                         SignalHandler,
                                         NewRecordHandler)
        self.signal_collector = SignalCollector()
        self.stream_manager = VideoStreamManager()
        self.stream_manager.set_signal_handler(self.signal_collector)
        self.stream_manager.set_camera_list_updater(ActiveCameras)
        self.video_manager = VideoRequestManager()
        self.video_manager.set_signal_handler(self.signal_collector)

    def prepare_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.background_tasks.add(self.loop.create_task(
            self.signal_collector.run_manager()))
        self.background_tasks.add(self.loop.create_task(
            self.stream_manager.run_manager()))
        self.background_tasks.add(self.loop.create_task(
            self.video_manager.run_manager()))
        self.background_tasks.add(self.loop.create_task(
            self.internal_server.run_server()))
        self.background_tasks.add(self.loop.create_task(
            self.external_server.run_server()))
        for task in self.background_tasks:
            task.add_done_callback(self.background_tasks.discard)
        return self.loop

    def run(self):
        self.loop.run_forever()

    def shutdown(self):
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            while self.loop.is_running():
                time.sleep(0.1)
        tasks = asyncio.all_tasks(loop=self.loop)
        if tasks:
            for task in tasks:
                task.cancel()
            group = asyncio.gather(*tasks, return_exceptions=True)
            self.loop.run_until_complete(group)
        self.loop.close()


if __name__ == '__main__':
    server = Server()
    server.prepare_loop()
    try:
        server.run()
    except KeyboardInterrupt:
        server.shutdown()
