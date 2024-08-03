import sys
import datetime
import pytz
from django.test import TransactionTestCase
from asgiref.sync import async_to_sync
from unittest.mock import patch, AsyncMock
from django.contrib.auth import get_user_model
from pathlib import Path
from ..models import ArchiveVideo, Camera

base_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(1, str(base_dir))

from camera_conn.db import (BaseRecordHandler,
                            NewVideoRecord,
                            CameraRecord,
                            UserRecord,
                            ActiveCameras)
from camera_conn.cam_server import RequestBuilder


timezone = pytz.timezone('Europe/Moscow')
User = get_user_model()


# -----------------------------------------------
# ------------ BaseRecordHandler ----------------
# -----------------------------------------------

class TestBaseRecordHandler(TransactionTestCase):

    def setUp(self):
        builder = RequestBuilder().with_args(writer=AsyncMock(),
                                             reader=AsyncMock())
        self.request = builder.build()
        self.test_object = BaseRecordHandler(self.request)
        self.test_object.save_record = AsyncMock()
        self.test_record = 'test_record'

        builder = RequestBuilder().with_args(status='success')
        self.success_response = builder.build()
        builder = RequestBuilder().with_args(status='failed')
        self.failed_response = builder.build()

    @patch('camera_conn.db.connect_to_db')
    @async_to_sync
    async def test_connect_to_db_failed(self, connect_to_db):
        connect_to_db.return_value = (None, None)
        result = await self.test_object.save()
        connect_to_db.assert_called_once()
        self.assertEqual(result, 'Failed to connect to DB')

    @patch('camera_conn.db.connect_to_db')
    @async_to_sync
    async def test_success_process_record(self, connect_to_db):
        connect_to_db.return_value = (AsyncMock(), AsyncMock())
        self.test_object.save_record.side_effect = None
        await self.test_object.save_queue.put(self.test_record)
        result = await self.test_object.save()
        self.test_object.save_record.assert_awaited_with(self.test_record)
        self.assertEqual(result, 'Transaction succseed')
        self.request \
            .writer \
            .write \
            .assert_called_with(self.success_response.serialize().encode())

    @patch('camera_conn.db.connect_to_db')
    @async_to_sync
    async def test_failed_process_record(self, connect_to_db):
        connect_to_db.return_value = (AsyncMock(), AsyncMock())
        self.test_object.save_record.side_effect = KeyError
        await self.test_object.save_queue.put(self.test_record)
        result = await self.test_object.save()
        self.assertEqual(result, 'Transaction failed')
        self.request \
            .writer \
            .write \
            .assert_called_with(self.failed_response.serialize().encode())


# -----------------------------------------------
# ------------ NewVideo record  -----------------
# -----------------------------------------------

class TestNewVideoRecord(TransactionTestCase):

    def setUp(self):
        builder = RequestBuilder().with_args(writer=AsyncMock(),
                                             reader=AsyncMock())
        self.request = builder.build()
        self.test_object = NewVideoRecord(self.request)
        self.time_1 = datetime.datetime.now(tz=timezone)
        self.time_2 = datetime.datetime.now(tz=timezone) + \
            datetime.timedelta(days=10)
        self.camera_name = 'test'
        Camera.objects.create(camera_name=self.camera_name,
                              is_active=True)
        self.record_1 = {'date_created': self.time_1.isoformat(),
                         'human_det': False,
                         'cat_det': False,
                         'car_det': False,
                         'chiken_det': False,
                         'camera_id': self.camera_name}
        self.record_2 = {'date_created': self.time_2.isoformat(),
                         'human_det': False,
                         'cat_det': False,
                         'car_det': False,
                         'chiken_det': False,
                         'camera_id': self.camera_name}
        self.corrupted_record = {'date_created': self.time_1.isoformat(),
                                 'human_det': False,
                                 'c111at_det': 'abrakadabra',
                                 'car_det': False,
                                 'chiken_det': False,
                                 'camera_id': self.camera_name}

    @async_to_sync
    async def tearDown(self):
        while self.test_object.save_queue.qsize() > 0:
            await self.test_object.save_queue.get()

    @async_to_sync
    async def test_record_saved(self):
        await self.test_object.save_queue.put(self.record_1)
        result = await self.test_object.save()
        records = []
        async for item in ArchiveVideo.objects.all().select_related('camera'):
            records.append(item)
        self.assertEqual(result, 'Transaction succseed')
        self.assertEqual(len(records), 1)
        self.assertEqual(self.time_1, records[0].date_created)
        self.assertEqual(self.camera_name, records[0].camera.camera_name)

    @async_to_sync
    async def test_corrupted_record_fail(self):
        await self.test_object.save_queue.put(self.corrupted_record)
        result = await self.test_object.save()
        records = []
        async for item in ArchiveVideo.objects.all():
            records.append(item)
        self.assertEqual(result, 'Transaction failed')
        self.assertEqual(len(records), 0)

    @async_to_sync
    async def test_multiple_records_saved(self):
        await self.test_object.save_queue.put(self.record_1)
        await self.test_object.save_queue.put(self.record_2)
        result = await self.test_object.save()
        records = []
        async for item in ArchiveVideo.objects.all():
            records.append(item)
        self.assertEqual(result, 'Transaction succseed')
        self.assertEqual(len(records), 2)

    @async_to_sync
    async def test_multiple_corrupted_records_fail(self):
        await self.test_object.save_queue.put(self.corrupted_record)
        await self.test_object.save_queue.put(self.record_1)
        await self.test_object.save_queue.put(self.record_2)
        result = await self.test_object.save()
        records = []
        async for item in ArchiveVideo.objects.all():
            records.append(item)
        self.assertEqual(result, 'Transaction failed')
        self.assertEqual(len(records), 0)


# -----------------------------------------------
# ------------ Camera Record  -------------------
# -----------------------------------------------

class TestCameraRecord(TransactionTestCase):

    def setUp(self):
        builder = RequestBuilder().with_args(writer=AsyncMock(),
                                             reader=AsyncMock())
        self.request = builder.build()
        self.test_object = CameraRecord(self.request)
        self.test_camera_record_1 = {'camera_name': 'test_camera_1'}
        self.test_camera_record_2 = {'camera_name': 'test_camera_2'}
        self.test_corrupted_record = {'corrupted'}

    @async_to_sync
    async def tearDown(self):
        while self.test_object.save_queue.qsize() > 0:
            await self.test_object.save_queue.get()

    @async_to_sync
    async def test_save_new_camera(self):
        await self.test_object.save_queue.put(self.test_camera_record_1)
        result = await self.test_object.save()
        records = []
        async for item in Camera.objects.filter(is_active=True):
            records.append(item)
        self.assertEqual(result, 'Transaction succseed')
        self.assertEqual(len(records), 1)
        self.assertEqual(self.test_camera_record_1['camera_name'],
                         records[0].camera_name)

    @async_to_sync
    async def test_update_camera(self):
        await self.test_object.save_queue.put(self.test_camera_record_1)
        await self.test_object.save()
        await self.test_object.save_queue.put(self.test_camera_record_1)
        result = await self.test_object.save()
        records = []
        async for item in Camera.objects.filter(is_active=True):
            records.append(item)
        self.assertEqual(len(records), 1)
        self.assertEqual(self.test_camera_record_1['camera_name'],
                         records[0].camera_name)
        self.assertEqual(result, 'Transaction succseed')

    @async_to_sync
    async def test_nonactive_camera_no_update(self):
        await self.test_object.save_queue.put(self.test_camera_record_1)
        await self.test_object.save_queue.put(self.test_camera_record_2)
        await self.test_object.save()
        await self.test_object.save_queue.put(self.test_camera_record_1)
        result = await self.test_object.save()
        records = []
        async for item in Camera.objects.filter(is_active=True):
            records.append(item)
        self.assertEqual(result, 'Transaction succseed')
        self.assertEqual(1, len(records))
        self.assertEqual(self.test_camera_record_1['camera_name'],
                         records[0].camera_name)
        records = []
        async for item in Camera.objects.filter(is_active=False):
            records.append(item)
        self.assertEqual(1, len(records))
        self.assertEqual(self.test_camera_record_2['camera_name'],
                         records[0].camera_name)

    @async_to_sync
    async def test_multiple_cameras_update(self):
        await self.test_object.save_queue.put(self.test_camera_record_1)
        await self.test_object.save_queue.put(self.test_camera_record_2)
        result = await self.test_object.save()
        records = []
        async for item in Camera.objects.filter(is_active=True):
            records.append(item)
        self.assertEqual(result, 'Transaction succseed')
        self.assertEqual(2, len(records))

    @async_to_sync
    async def test_corrupted_record_handling(self):
        await self.test_object.save_queue.put(self.test_corrupted_record)
        result = await self.test_object.save()
        records = []
        async for item in Camera.objects.filter(is_active=True):
            records.append(item)
        self.assertEqual(result, 'Transaction failed')
        self.assertEqual(0, len(records))

    @async_to_sync
    async def test_multiple_corrupted_record_handling(self):
        await self.test_object.save_queue.put(self.test_camera_record_1)
        await self.test_object.save_queue.put(self.test_camera_record_2)
        await self.test_object.save_queue.put(self.test_corrupted_record)
        result = await self.test_object.save()
        records = []
        async for item in Camera.objects.filter(is_active=True):
            records.append(item)
        self.assertEqual(result, 'Transaction failed')
        self.assertEqual(0, len(records))


# -----------------------------------------------
# ------------ User record  ---------------------
# -----------------------------------------------

class TestUserRecord(TransactionTestCase):

    def setUp(self):
        builder = RequestBuilder().with_args(writer=AsyncMock(),
                                             reader=AsyncMock())
        self.request = builder.build()
        self.test_object = UserRecord(self.request)
        self.record_accepted = {'request_result': 'aproved',
                                'username': 'username_1'}
        self.record_denied = {'request_result': 'denied',
                              'username': 'username_2'}
        self.corrupted_record = {'corrupted'}
        self.pk_accepted = User.objects.create_user(
                         username='username_1',
                         email='1@mail.ru',
                         password='123',
                         is_active=False,
                         admin_checked=False).pk
        self.pk_denied = User.objects.create_user(
                         username='username_2',
                         email='2@mail.ru',
                         password='123',
                         is_active=False,
                         admin_checked=False).pk

    @async_to_sync
    async def test_accept_user(self):
        await self.test_object.save_queue.put(self.record_accepted)
        result = await self.test_object.save()
        user = await User.objects.aget(pk=self.pk_accepted)
        self.assertTrue(user.is_active)
        self.assertEqual(result, 'Transaction succseed')
        self.assertTrue(user.admin_checked)

    @async_to_sync
    async def test_deny_user(self):
        await self.test_object.save_queue.put(self.record_denied)
        result = await self.test_object.save()
        user = await User.objects.aget(pk=self.pk_denied)
        self.assertFalse(user.is_active)
        self.assertEqual(result, 'Transaction succseed')
        self.assertTrue(user.admin_checked)

    @async_to_sync
    async def test_handle_multiple_user_records(self):
        await self.test_object.save_queue.put(self.record_accepted)
        await self.test_object.save_queue.put(self.record_denied)
        result = await self.test_object.save()
        user_1 = await User.objects.aget(pk=self.pk_accepted)
        self.assertTrue(user_1.is_active)
        self.assertTrue(user_1.admin_checked)
        user_2 = await User.objects.aget(pk=self.pk_denied)
        self.assertFalse(user_2.is_active)
        self.assertTrue(user_2.admin_checked)
        self.assertEqual(result, 'Transaction succseed')

    @async_to_sync
    async def test_corrupted_record(self):
        await self.test_object.save_queue.put(self.corrupted_record)
        result = await self.test_object.save()
        self.assertEqual(result, 'Transaction failed')

    @async_to_sync
    async def test_multiple_records_with_corrupted(self):
        await self.test_object.save_queue.put(self.record_accepted)
        await self.test_object.save_queue.put(self.record_denied)
        await self.test_object.save_queue.put(self.corrupted_record)
        result = await self.test_object.save()
        self.assertEqual(result, 'Transaction failed')
        user_1 = await User.objects.aget(pk=self.pk_accepted)
        user_2 = await User.objects.aget(pk=self.pk_denied)
        self.assertFalse(user_1.is_active)
        self.assertFalse(user_2.is_active)


# -----------------------------------------------
# ------------- Active Camera -------------------
# -----------------------------------------------

class TestActiveCameras(TransactionTestCase):

    def setUp(self):
        self.test_object = ActiveCameras
        Camera.objects.create(camera_name='active_camera', is_active=True)
        Camera.objects.create(camera_name='disabled_camera', is_active=False)

    @async_to_sync
    async def test_get_list(self):
        result = await self.test_object.get_active_camera_list()
        self.assertEqual(result[0][0], 'active_camera')
        self.assertEqual(len(result), 1)
