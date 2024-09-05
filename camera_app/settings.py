import pytz
import os
import logging
import configparser
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s | %(levelname)s | %(asctime)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",)

base_dir = Path(__file__).resolve().parent.parent

SAVE_PATH = base_dir / 'video_archive/'
if not os.path.isdir(SAVE_PATH):
    os.mkdir(SAVE_PATH)

MODEL_PATH = base_dir / 'camera_app/weights/test_weights.pt'
TIMEZONE = pytz.timezone('Europe/Moscow')

config = configparser.ConfigParser()
config.read(base_dir / 'camera_app/settings.cfg')

# CONNECTION SETTINGS
SERVER_HOST = config['SERVER']['SERVER_HOST']
SERVER_PORT = int(config['SERVER']['SERVER_PORT'])
GET_SERVER_EVENTS_TIMEOUT = int(config['SERVER']['GET_SERVER_EVENTS_TIMEOUT'])
SOCKET_BUFF_SIZE = int(config['SERVER']['SOCKET_BUFF_SIZE'])
RECONNECTION_TIMEOUT = int(config['SERVER']['RECONNECTION_TIMEOUT'])
MAX_RECORDS = int(config['SERVER']['MAX_RECORDS'])

# EMAIL SETTINGS
EMAIL_ENABLED = bool(int(config['EMAIL']['EMAIL_ENABLED']))
EMAIL_USER = config['EMAIL']['EMAIL_USER']
EMAIL_PASSWORD = config['EMAIL']['EMAIL_PASSWORD']
EMAIL_PORT = int(config['EMAIL']['EMAIL_PORT'])
EMAIL_BACKEND = config['EMAIL']['EMAIL_BACKEND']

# USER LIST
APROVED_USER_LIST = config['USER_LIST']['APROVED_USER_LIST'].split(' ')
APROVE_ALL = bool(int(config['USER_LIST']['APROVE_ALL']))

# CAMERA LIST
cam_list = config['CAMERA_LIST'].keys()
CAMERA_LIST = {}
for camera in cam_list:
    try:
        source = int(config['CAMERA_LIST'][camera])
    except ValueError:
        source = config['CAMERA_LIST'][camera]
    CAMERA_LIST.update({camera: source})

# DETECTION SETTINGS
MAX_VIDEO_LENGTH = int(config['DETECTION']['MAX_VIDEO_LENGTH'])
DEFAULT_DETECTION = bool(int(config['DETECTION']['DEFAULT_DETECTION']))
CONFIDENCE = float(config['DETECTION']['CONFIDENCE'])
SAVE_FRAME_TIMEOUT = int(config['DETECTION']['SAVE_FRAME_TIMEOUT'])
NO_DETECTION_LEN = int(config['DETECTION']['NO_DETECTION_LEN'])
FPS = int(config['DETECTION']['FPS'])
