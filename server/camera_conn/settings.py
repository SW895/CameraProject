import os
import logging


logging.basicConfig(
    level=logging.ERROR,
    format="%(name)s | %(levelname)s | %(asctime)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",)

DEBUG = bool(os.environ.get('DEBUG', 1))
GLOBAL_TEST = True
STREAM_SOURCE_TIMEOUT = int(os.environ.get('STREAM_SOURCE_TIMEOUT', '5'))
VIDEO_REQUEST_TIMEOUT = int(os.environ.get('VIDEO_REQUEST_TIMEOUT', '5'))
GARB_COLLECTOR_TIMEOUT = int(os.environ.get('GARB_COLLECTOR_TIMEOUT', '10'))

# POSTGRES
if GLOBAL_TEST:
    # SAME AS IN DJANGO DATABASE SETTINGS test_db
    DB_NAME = 'test_base'
    DB_USER = 'test_user'
    DB_PASSWORD = 'test_password'
    DB_HOST = 'localhost'
    DB_PORT = 10000
else:
    if DEBUG:
        DB_NAME = 'test_dj_test'
    else:
        DB_NAME = os.environ.get('POSTGRES_DB', 'dj_test')
    DB_USER = os.environ.get('POSTGRES_USER', 'test_dj')
    DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD', '123')
    DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
    DB_PORT = os.environ.get('POSTGRES_PORT', '5432')


# SOCKET SETTINGS
EXTERNAL_HOST = os.environ.get('EXTERNAL_HOST', '127.0.0.1')
EXTERNAL_PORT = int(os.environ.get('EXTERNAL_PORT', 10900))
EXTERNAL_CONN_QUEUE = int(os.environ.get('EXTERNAL_CONNECTION_QUEUE', 10))

INTERNAL_HOST = os.environ.get('INTERNAL_HOST', '127.0.0.1')
INTERNAL_PORT = int(os.environ.get('INTERNAL_PORT', 20900))
INTERNAL_CONN_QUEUE = int(os.environ.get('INTERNAL_CONNECTION_QUEUE', 10))

SOCKET_BUFF_SIZE = int(os.environ.get('SOCKET_BUFF_SIZE', '65536'))
