import json
import sys
from client_responses import BaseConnection
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(1, str(base_dir))
from cam_server import RequestBuilder
from settings import TEST_CAMERA_NUM


class BaseRecord(BaseConnection):

    async def run(self):
        reader, writer = await self.get_connection(self.request)
        writer.write(self.record.encode())
        await writer.drain()
        reply = await reader.read(self.buff_size)
        writer.close()
        await writer.wait_closed()
        return reply.decode()


class RegisterCameras(BaseRecord):

    def __init__(self):
        cam_list = []
        for test_camera in range(TEST_CAMERA_NUM):
            camera_name = f'test_camera_{test_camera}'
            cam_list.append({'camera_name': camera_name})
        self.record = ''
        for item in cam_list:
            self.record += json.dumps(item) + '\n'

        builder = RequestBuilder().with_args(request_type='new_camera_record',
                                             record_size=len(self.record))
        self.request = builder.build()


class NewVideoRecord(BaseRecord):

    def __init__(self):
        new_record = {
            'date_created': '2024-01-22 18:38:37.160000+3:00',
            'car_det': True,
            'cat_det': False,
            'chiken_det': False,
            'human_det': False,
            'camera_id': 'test_camera_1'}
        self.record = json.dumps(new_record) + '\n'
        builder = RequestBuilder().with_args(request_type='new_video_record',
                                             record_size=len(self.record))
        self.request = builder.build()
