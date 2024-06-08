from main_thread import ClientRequest, CameraClient
import configparser
import os
import logging
config = configparser.ConfigParser()
config.read('camera.ini')

test_object = CameraClient(config)
test_object.DEBUG = True
#mock_socket = Mock()
video_name = '2021-04-23T14:12:12'
request = ClientRequest(request_type='video_request',
                                video_name='2021-04-23T14:12:12|test',)
wrong_request = ClientRequest(request_type='video_request',
                                    video_name='2023-04-23T14:12:12|test',)
save_path = test_object.save_path / (video_name.split('T')[0])
full_video_name = save_path / (video_name + '.mp4')
video_size = 125000
logging.critical('%s', test_object.save_path)
logging.critical('%s', save_path)
if not os.path.isdir(test_object.save_path):
    
    os.mkdir(test_object.save_path)
if not os.path.isdir(save_path):
    
    os.mkdir(save_path)
with open(full_video_name, 'wb') as video:
    video.write(bytes(video_size))