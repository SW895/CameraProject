import asyncio
import logging
import threading
from client import (RegisterCameras,)
from backend import (StreamRequest,
                     )
#from utils import new_thread, set_up_server, set_up_client

import threading
import asyncio
import sys
import subprocess
import time
from client import (TestClient,
                    SignalConnection,
                    StreamConnection,)
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(base_dir))
from settings import (DB_NAME,
                      DB_HOST,
                      DB_PASSWORD,
                      DB_PORT,
                      DB_USER,
                      DEBUG)
from run_server import Server
from utils import Database, new_thread

test_results = {}
loop_list = []
mutex = threading.Lock()

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
    #loop = asyncio.new_event_loop()
    #loop.create_task(main())
    #add_loop_to_list(loop)
    #loop.run_forever()
    server = Server()
    loop_list.append(server)
    server.run()


#def set_up_client():
#    client = client_thread()
#    return client


def set_up_server():
    database = Database()
    database.prepare_test_database()
    camera_conn_server = camera_conn_thread()
    time.sleep(2)
    return database, camera_conn_server


def add_loop_to_list(loop):
    global loop_list
    with mutex:
        loop_list.append(loop)


#@new_thread
#def test_reg_cam():
#    loop = asyncio.new_event_loop()
#    
#    task = loop.create_task(RegisterCameras().run())
#    response = loop.run_until_complete(task)
#    test_results.update({'CAMERA_REGISTRATION': response})


def main_test():
    #database, _ = set_up_server()
    database = Database()
    database.prepare_test_database()
    th = camera_conn_thread()
    time.sleep(2)
    #test_camera_reg = test_reg_cam()
    #test_camera_reg.join()

    for result in test_results:
        if test_results[result]:
            logging.critical('%s........OK', result)

    database.cleanup_test_database()
    #loop_list[0].loop.call_soon_threadsafe(loop_list[0].loop.stop)
    #time.sleep(1)
    loop_list[0].shutdown()
    th.join()


if __name__ == "__main__":
    main_test()
