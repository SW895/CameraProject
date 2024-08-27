import os
import pytz
import logging
import configparser
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s | %(levelname)s | %(asctime)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",)
config = configparser.ConfigParser()
config.read('camera.ini')


DEBUG = bool(os.environ.get('DEBUG', 1))

base_dir = Path(__file__).resolve().parent.parent
SAVE_PATH = base_dir / 'video_archive/'
MODEL_PATH = base_dir / 'camera_app/weights/test_weights.pt'
TIMEZONE = pytz.timezone('Europe/Moscow')
"""
# CONNECTION SETTINGS
SERVER_HOST = config['SERVER']['SERVER_HOST']
SERVER_PORT = int(config['SERVER']['SERVER_PORT'])
GET_SERVER_EVENTS_TIMEOUT = int(config['SERVER']['GET_SERVER_EVENTS_TIMEOUT'])
SOCKET_BUFF_SIZE = int(config['SERVER']['SOCKET_BUFF_SIZE'])
RECONNECTION_TIMEOUT = int(config['SERVER']['RECONNECTION_TIMEOUT'])

# EMAIL SETTINGS
EMAIL_USER = config['EMAIL']['EMAIL_USER']
EMAIL_PASSWORD = config['EMAIL']['EMAIL_PASSWORD']
EMAIL_PORT = int(config['EMAIL']['EMAIL_PORT'])
EMAIL_BACKEND = 'smtp.gmail.com'

# USER LIST
USER_LIST = config['USER']['USER_LIST'].split(' ')
APROVE_ALL = bool(config['USER']['APROVE_ALL'])

# CAMERA LIST
cam_list = config['CAMERA_LIST'].keys()
CAMERA_LIST = {}
for camera in cam_list:
    CAMERA_LIST.update({camera: config['CAMERA_LIST'][camera]})

# DETECTION SETTINGS
BUFF_SIZE = 100
"""

# CONNECTION SETTINGS
SERVER_HOST = '127.0.01'
SERVER_PORT = 10900
GET_SERVER_EVENTS_TIMEOUT = 1
SOCKET_BUFF_SIZE = 65536
RECONNECTION_TIMEOUT = 1

# EMAIL SETTINGS
EMAIL_USER = 'user'
EMAIL_PASSWORD = 'pass'
EMAIL_PORT = 587
EMAIL_BACKEND = 'smtp.gmail.com'

# USER LIST
USER_LIST = ['moreau', 'test_user']
APROVE_ALL = False

# CAMERA LIST
cam_list = {'test_camera': 0}
CAMERA_LIST = {}
for camera in cam_list:
    CAMERA_LIST.update({camera: cam_list[camera]})

# DETECTION SETTINGS
BUFF_SIZE = 100
