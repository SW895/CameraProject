import threading
import docker
import sys
import subprocess
import time
import psycopg
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(1, str(base_dir))
from settings import (DB_NAME,
                      DB_HOST,
                      DB_PASSWORD,
                      DB_PORT,
                      DB_USER,
                      DEBUG)


class TestDatabase:

    def prepare_local_database(self):
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

    def cleanup_local_database(self):
        subprocess.run(f'PGPASSWORD={DB_PASSWORD} \
                        dropdb {self.database} \
                        -U {DB_USER} \
                        -h {DB_HOST} \
                        -p {DB_PORT}', shell=True)

    def prepare_db_container(self):
        env = {
            'POSTGRES_DB': DB_NAME,
            'POSTGRES_USER': DB_USER,
            'POSTGRES_PASSWORD': DB_PASSWORD,
            'POSTGRES_HOST': DB_HOST,
            'POSTGRES_PORT': DB_PORT,
            'PGTZ': 'GMT+3',
        }
        self.container_name = 'test_db'
        self.client = docker.from_env()
        self.container = self.client.containers.run(
            'postgres:15',
            environment=env,
            name=self.container_name,
            ports={'5432/tcp': DB_PORT},
            detach=True)

        while True:
            try:
                conn = psycopg.connect(
                    dbname=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=DB_HOST,
                    port=DB_PORT)
                conn.close()
            except psycopg.OperationalError:
                time.sleep(0.1)
            else:
                break

        subprocess.run(f'python {base_dir.parent}/djbackend/manage.py migrate \
                       --database test_db',
                       shell=True)

    def cleanup_db_container(self):
        self.container.stop()
        self.container.remove()


def new_thread(target_function):

    def inner(*args, **kwargs):

        thread = threading.Thread(target=target_function,
                                  args=args,
                                  kwargs=kwargs)
        thread.start()
        return thread

    return inner
