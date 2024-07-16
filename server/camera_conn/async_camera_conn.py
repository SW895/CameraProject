import asyncio
import os
import socket
import logging
from cam_server import Server
from managers import VideoStreamManager, VideoRequestManager
from handlers import (
                        VideoStreamRequestHandler,
                        VideoStreamResponseHandler,
                        SignalHandler,
                        NewRecordHandler,
                        VideoRequestHandler,
                        VideoResponseHandler,
                        AproveUserRequestHandler,
                        AproveUserResponseHandler
                        )


logging.basicConfig(level=logging.DEBUG,
                    format="%(name)s | %(levelname)s | \
                    %(asctime)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                    )

external_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
external_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
external_sock.bind((os.environ.get('EXTERNAL_HOST', '127.0.0.1'),
                    int(os.environ.get('EXTERNAL_PORT', 10900))))
external_sock.listen(10)

internal_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
internal_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
internal_sock.bind((os.environ.get('INTERNAL_HOST', '127.0.0.1'),
                    int(os.environ.get('INTERNAL_PORT', 20900))))
internal_sock.listen(10)

internal_server = Server(internal_sock)
external_server = Server(external_sock)
internal_server.add_handler(VideoStreamRequestHandler,
                            VideoRequestHandler,
                            AproveUserRequestHandler)
external_server.add_handler(VideoStreamResponseHandler,
                            VideoResponseHandler,
                            AproveUserResponseHandler,
                            SignalHandler,
                            NewRecordHandler)
stream_manager = VideoStreamManager(SignalHandler)
video_manager = VideoRequestManager(SignalHandler)

loop = asyncio.get_event_loop()
loop.create_task(stream_manager.run_manager())
loop.create_task(video_manager.run_manager())
loop.create_task(internal_server.run_server())
loop.create_task(external_server.run_server())
loop.run_forever()
