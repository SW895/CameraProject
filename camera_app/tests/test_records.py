from utils import get_connection
from main_thread import ClientRequest
import json
import datetime
import pytz
import os
from pathlib import Path

server_address = '127.0.0.1'
server_port = 10900
timezone = pytz.timezone('Europe/Moscow')
base_dir = Path(__file__).resolve().parent.parent
new_record = ''

request = ClientRequest(request_type='new_record', camera_name='1')
sock_camera = get_connection(request,
                    attempts_num=1,
                    server_address=server_address,
                    server_port=server_port)
       
records = json.dumps({'camera_name':'test_camera_1'}) + "\n"
records += json.dumps({'camera_name':'test_camera_2'}) + "\n"

if sock_camera:
    try:
        sock_camera.send(records.encode())
    except:
        pass
    sock_camera.close()

current_time = datetime.datetime.now(tz=timezone)

video_record_1 = {'date_created':"22_01_2024T18:38:37.160934+03:00",
                  'car_det': True,
                  'cat_det':False,
                  'chiken_det':False,
                  'human_det':False,
                  'camera_id':'test_camera_1'}
video_record_2 = {'date_created':"09_09_2024T11:38:37.160934+03:00",
                  'car_det': False,
                  'cat_det':True,
                  'chiken_det':False,
                  'human_det':False,
                  'camera_id':'test_camera_1'}
video_record_3 = {'date_created':"10_06_2024T19:22:37.160934+03:00",
                  'car_det': False,
                  'cat_det':False,
                  'chiken_det':True,
                  'human_det':False,
                  'camera_id':'test_camera_2'}
video_record_4 = {'date_created':"18_05_2023T21:38:37.160934+03:00",
                  'car_det': False,
                  'cat_det':False,
                  'chiken_det':False,
                  'human_det':True,
                  'camera_id':'test_camera_2'}


records = [video_record_1, video_record_2, video_record_3, video_record_4]
for record in records:
    new_record += json.dumps(record) + '\n'

sock_video_record = get_connection(ClientRequest(request_type='new_record',
                                            db_record='new_item'), 
                                attempts_num=1,
                                server_address=server_address,
                                server_port=server_port)

if sock_video_record:
    try:
        sock_video_record.send(new_record.encode())
    except BrokenPipeError or ConnectionResetError:
        pass
    sock_video_record.close()