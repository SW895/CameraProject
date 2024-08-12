import asyncio
import logging
import json
import sys
import time
from utils import TestDatabase, new_thread
from backend_requests import (StreamRequest,
                              AproveUserRequest)
from client_record_requests import (RegisterCameras,
                                    NewVideoRecord,)
from client_responses import (TestClient,
                              SignalConnection,
                              StreamConnection,
                              UserAproveResponse)
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(1, str(base_dir))
from settings import GLOBAL_TEST
from run_server import Server


test_results = {}
camera_conn_server = None
client = None


# -----------------------------------------------
# ------------ Init section  --------------------
# -----------------------------------------------

@new_thread
def client_thread():
    global client
    client = TestClient()
    client.set_signal_connection(SignalConnection())
    client.add_handlers(StreamConnection(),
                        UserAproveResponse())
    client.prepare_loop()
    client.run_client()


def set_up_client():
    client_th = client_thread()
    time.sleep(1)
    return client_th


@new_thread
def camera_conn_thread():
    global camera_conn_server
    camera_conn_server = Server()
    camera_conn_server.prepare_loop()
    camera_conn_server.run()


def set_up_server():
    database = TestDatabase()
    database.prepare_db_container()
    camera_conn_server = camera_conn_thread()
    time.sleep(1)
    return database, camera_conn_server


# -----------------------------------------------
# ------------ Camera record test ---------------
# -----------------------------------------------

@new_thread
def test_reg_cam():
    loop = asyncio.new_event_loop()
    task = loop.create_task(RegisterCameras().run())
    response = loop.run_until_complete(task)
    test_results.update({'CAMERA REGISTRATION': json.loads(response)})


# -----------------------------------------------
# ------------ Video record test ----------------
# -----------------------------------------------

@new_thread
def test_new_video_record():
    loop = asyncio.new_event_loop()
    task = loop.create_task(NewVideoRecord().run())
    response = loop.run_until_complete(task)
    test_results.update({'ADD NEW VIDEO RECORD': json.loads(response)})


# -----------------------------------------------
# ------------ User record test -----------------
# -----------------------------------------------

@new_thread
def test_aprove_user_record():
    loop = asyncio.new_event_loop()
    task = loop.create_task(AproveUserRequest().run())
    loop.run_until_complete(task)

# -----------------------------------------------
# ------------ Video request test ---------------
# -----------------------------------------------


# -----------------------------------------------
# ------------ Stream test ----------------------
# -----------------------------------------------
def main():
    test_camera_reg = test_reg_cam()
    test_camera_reg.join()

    test_new_video = test_new_video_record()
    test_new_video.join()

    test_aprove_user = test_aprove_user_record()
    test_aprove_user.join()
    time.sleep(1)


if __name__ == "__main__":
    if GLOBAL_TEST:
        database, server_thread = set_up_server()
        client_th = set_up_client()
        main()
        database.cleanup_db_container()
        camera_conn_server.shutdown()
        server_thread.join()
        client.shutdown()
        client_th.join()
    else:
        logging.error('Set GLOBAL_TEST variable in settings.py to True')


print('TESTING SUMMARY:')
test_results.update(client.result)
for result in test_results:
    if test_results[result]:
        name = result.upper().replace('_', ' ')
        right_padding = name.ljust(40, '.')
        if test_results[result]['status'] == 'success':
            print(f'{right_padding}OK')
        else:
            print(f'{right_padding}FAILED')
