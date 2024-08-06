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


class Database:

    def prepare_test_database(self):
        if not DEBUG:
            self.template_name = DB_NAME
            self.database = 'test_' + DB_NAME
        else:
            self.template_name = DB_NAME[5:]
            self.database = DB_NAME
        subprocess.run(f'PGPASSWORD={DB_PASSWORD} \
                        createdb \
                        -U {DB_USER} \
                        -h "{DB_HOST}" \
                        -p {DB_PORT} {self.database} \
                        --template={self.template_name}', shell=True)

    def cleanup_test_database(self):
        subprocess.run(f'PGPASSWORD={DB_PASSWORD} \
                        dropdb {self.database} \
                        -U {DB_USER} \
                        -h {DB_HOST} \
                        -p {DB_PORT}', shell=True)


def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function,
                                  args=args,
                                  kwargs=kwargs)
        thread.start()
        return thread

    return inner

mutex = threading.Lock()
"""
@new_thread
def client_thread():
    loop = asyncio.new_event_loop()
    client = TestClient()
    client.set_signal_connection(SignalConnection())
    client.add_handlers(StreamConnection())
    loop.create_task(client.run_client())
    add_loop_to_list(loop)
    loop.run_forever()


@new_thread
def camera_conn_thread():
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    add_loop_to_list(loop)
    loop.run_forever()


def set_up_client():
    client = client_thread()
    return client


def set_up_server():
    database = Database()
    database.prepare_test_database()    
    camera_conn_server = camera_conn_thread()
    time.sleep(2)
    return database, camera_conn_server


def add_loop_to_list(loop):
    global loop_list
    with mutex:
        loop_list.append(loop)"""