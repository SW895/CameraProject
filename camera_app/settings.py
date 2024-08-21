import os
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

# CONNECTION SETTINGS
SERVER_HOST = config['SERVER']['SERVER_HOST']
SERVER_PORT = config['SERVER']['SERVER_PORT']
GET_SERVER_EVENTS_TIMEOUT = config['SERVER']['GET_SERVER_EVENTS_TIMEOUT']
SOKCET_BUFF_SIZE = config['SERVER']['SOKCET_BUFF_SIZE']
RECONNECTION_TIMEOUT = config['SERVER']['RECONNECTION_TIMEOUT']

# EMAIL SETTINGS
EMAIL_USER = config['EMAIL']['EMAIL_USER']
EMAIL_PASSWORD = config['EMAIL']['EMAIL_PASSWORD']
EMAIL_PORT = config['EMAIL']['EMAIL_PORT']
EMAIL_BACKEND = 'smtp.gmail.com'

# USER LIST
USER_LIST = config['USER']['USER_LIST'].split(' ')
APROVE_ALL = bool(config['USER'['APROVE_ALL']])

# CAMERA LIST
cam_list = config['CAMERA_LIST'].keys()
CAMERA_LIST = {}
for camera in cam_list:
    CAMERA_LIST.update({camera: config['CAMERA_LIST'][camera]})
