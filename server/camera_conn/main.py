import asyncio
import socket
from cam_server import Server
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


async def main():
    external_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    external_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    external_sock.bind((EXTERNAL_HOST, EXTERNAL_PORT))
    external_sock.listen(EXTERNAL_CONN_QUEUE)

    internal_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    internal_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    internal_sock.bind((INTERNAL_HOST, INTERNAL_PORT))
    internal_sock.listen(INTERNAL_CONN_QUEUE)

    internal_server = Server(internal_sock)
    external_server = Server(external_sock)
    internal_server.add_handler(VideoStreamRequestHandler,
                                VideoRequestHandler,
                                AproveUserRequestHandler)
    external_server.add_handler(VideoStreamResponseHandler,
                                VideoResponseHandler,
                                SignalHandler,
                                NewRecordHandler)
    signal_collector = SignalCollector()
    stream_manager = VideoStreamManager()
    stream_manager.set_signal_handler(signal_collector)
    stream_manager.set_camera_list_updater(ActiveCameras)
    video_manager = VideoRequestManager()
    video_manager.set_signal_handler(signal_collector)

    loop = asyncio.get_running_loop()
    loop.create_task(signal_collector.run_manager())
    loop.create_task(stream_manager.run_manager())
    loop.create_task(video_manager.run_manager())
    loop.create_task(internal_server.run_server())
    loop.create_task(external_server.run_server())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
