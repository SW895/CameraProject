import asyncio
import threading
import logging
import time
import sys
from pathlib import Path
from client import (TestClient,
                    SignalConnection,
                    RegisterCameras,
                    StreamConnection)
from backend import (StreamRequest)
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(base_dir))
from run_server import main
from settings import DEBUG

test_results = {}
register_camera_finished = threading.Event()
stream_test_finished = threading.Event()


def client_thread():
    loop = asyncio.new_event_loop()    
    client = TestClient()
    client.set_signal_connection(SignalConnection())
    client.add_handlers(StreamConnection())
    loop.create_task(client.run_client())
    loop.run_forever()


def test_reg_cam():
    loop = asyncio.new_event_loop()
    task = loop.create_task(RegisterCameras().run())
    response = loop.run_until_complete(task)
    test_results.update({'CAMERA REGISTRATION': response})
    register_camera_finished.set()


def backend_thread():
    loop = asyncio.new_event_loop()
    loop.run_forever()
    stream_request = loop.create_task(StreamRequest().run())
    response = loop.run_until_complete(stream_request)
    test_results.update({'STREAM': response})
    stream_test_finished.set()


def camera_conn_thread():
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()


def main_test():
    camera_conn = threading.Thread(target=camera_conn_thread)
    camera_conn.start()
    time.sleep(2)
    camera_reg = threading.Thread(target=test_reg_cam)
    camera_reg.start()
    register_camera_finished.wait()
    logging.critical('RESULT:%s', test_results['CAMERA_REGISTRATION'])


if __name__ == "__main__":
    main_test()

# loop.stop()
# loop.close()
