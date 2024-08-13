import asyncio
import logging
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
database = None
camera_conn_thread = None
client_thread = None


# -----------------------------------------------
# ------------ Init section  --------------------
# -----------------------------------------------

@new_thread
def run_client():
    global client
    client = TestClient()
    client.set_signal_connection(SignalConnection())
    client.add_handlers(StreamConnection(),
                        UserAproveResponse())
    client.prepare_loop()
    client.run_client()


@new_thread
def run_server():
    global camera_conn_server
    camera_conn_server = Server()
    camera_conn_server.prepare_loop()
    camera_conn_server.run()


def set_up_testing_env():
    global database, camera_conn_thread, client_thread
    database = TestDatabase()
    database.prepare_db_container()
    camera_conn_thread = run_server()
    client_thread = run_client()
    time.sleep(1)


def clean_up_testing_env():
    global client, camera_conn_server, database
    global camera_conn_thread, client_thread
    database.cleanup_db_container()
    camera_conn_server.shutdown()
    camera_conn_thread.join()
    client.shutdown()
    client_thread.join()


# -----------------------------------------------
# ------------ Camera record test ---------------
# -----------------------------------------------

@new_thread
def test_reg_cam():
    loop = asyncio.new_event_loop()
    task = loop.create_task(RegisterCameras().run())
    response = loop.run_until_complete(task)
    if response['status'] == 'success':
        result = True
    else:
        result = False
    test_results.update({'CAMERA REGISTRATION': result})


# -----------------------------------------------
# ------------ Video record test ----------------
# -----------------------------------------------

@new_thread
def test_new_video_record():
    loop = asyncio.new_event_loop()
    task = loop.create_task(NewVideoRecord().run())
    response = loop.run_until_complete(task)
    if response['status'] == 'success':
        result = True
    else:
        result = False
    test_results.update({'ADD NEW VIDEO RECORD': result})


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

@new_thread
def test_stream_request():
    loop = asyncio.new_event_loop()
    task = loop.create_task(StreamRequest().run())
    response = loop.run_until_complete(task)
    if response['corrupted_frames'] / response['good_frames'] < 0.01:
        result = True
    else:
        result = False
    test_results.update({'SINGLE STREAM REQUEST': result})


# -----------------------------------------------
# ------------ MAIN -----------------------------
# -----------------------------------------------

def main():
    print('Wait for all tests to finish')
    test_camera_reg = test_reg_cam()
    test_camera_reg.join()

    test_new_video = test_new_video_record()
    test_new_video.join()

    test_aprove_user = test_aprove_user_record()
    test_aprove_user.join()

    test_stream = test_stream_request()
    test_stream.join()


def print_results():
    global client
    global test_results
    print('TESTING SUMMARY:')
    test_results.update(client.result)
    for result in test_results:
        if test_results[result]:
            right_padding = result.ljust(40, '.')
            if test_results[result]:
                print(f'{right_padding}OK')
            else:
                print(f'{right_padding}FAILED')


if __name__ == "__main__":
    if GLOBAL_TEST:
        set_up_testing_env()
        main()
        print_results()
        clean_up_testing_env()
    else:
        logging.error('Set GLOBAL_TEST variable in \
                      server/camera_conn/settings.py to True')
