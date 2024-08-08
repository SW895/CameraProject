import asyncio
import logging
import json
import sys
import time
from utils import TestDatabase, new_thread
from fake_backend import (StreamRequest,)
from fake_client import (TestClient,
                         RegisterCameras,
                         SignalConnection,
                         StreamConnection,)
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(base_dir))
from settings import GLOBAL_TEST
from run_server import Server


test_results = {}
camera_conn_server = None
fake_client = None

#@new_thread
#def client_thread():
#    loop = asyncio.new_event_loop()
#    client = TestClient()
#    client.set_signal_connection(SignalConnection())
#    client.add_handlers(StreamConnection())
#    loop.create_task(client.run_client())
#    add_loop_to_list(loop)
#    loop.run_forever()


@new_thread
def camera_conn_thread():
    global camera_conn_server
    server = Server()
    server.prepare_loop()
    camera_conn_server = server
    server.run()


def set_up_server():
    database = TestDatabase()
    database.prepare_db_container()
    camera_conn_server = camera_conn_thread()
    time.sleep(1)
    return database, camera_conn_server


@new_thread
def test_reg_cam():
    loop = asyncio.new_event_loop()
    task = loop.create_task(RegisterCameras().run())
    response = loop.run_until_complete(task)
    test_results.update({'CAMERA_REGISTRATION': json.loads(response)})


def main_test():
    test_camera_reg = test_reg_cam()
    test_camera_reg.join()


if __name__ == "__main__":
    if GLOBAL_TEST:
        database, server_thread = set_up_server()
        main_test()
        database.cleanup_db_container()
        camera_conn_server.shutdown()
        server_thread.join()
    else:
        logging.error('Set GLOBAL_TEST variable in settings.py to True')


print('TESTING SUMMARY:')
for result in test_results:
    if test_results[result]:
        if test_results[result]['status'] == 'success':
            print(f'{result}........OK')
        else:
            print(f'{result}........FAILED')
