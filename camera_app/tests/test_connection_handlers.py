import pytest
import asyncio
import sys
import json
import os
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(base_dir))
from settings import SAVE_PATH
from streaming import VideoStreamManager
from connection_handlers import (
    AproveUserHandler,
    VideoRequestHandler,
    StreamHandler
)
from request_builder import RequestBuilder

pytest_plugins = ('pytest_asyncio', )
camera_name = 'test_camera'
test_video_name = 'test_video'
test_time = 'test_time'


@pytest.fixture
def wrong_event():
    builder = RequestBuilder().with_args(request_type='wrong_event')
    return builder.build()


# -----------------------------------------------
# ------------ Test Aprove User Handler ---------
# -----------------------------------------------

@pytest.fixture
def aprove_user_handler(mocker):
    handler = AproveUserHandler
    handler.send_email = mocker.Mock()
    handler.connect_to_server = mocker.AsyncMock()
    return handler


@pytest.fixture
def status_failed(mocker):
    builder = RequestBuilder().with_args(status='failed')
    response = builder.build()
    reader = mocker.AsyncMock()
    reader.read.return_value = response.serialize().encode()
    return reader


@pytest.fixture
def status_success(mocker):
    builder = RequestBuilder().with_args(status='success')
    response = builder.build()
    reader = mocker.AsyncMock()
    reader.read.return_value = response.serialize().encode()
    return reader


@pytest.fixture
def aproved_user():
    builder = RequestBuilder().with_args(request_type='aprove_user_request',
                                         username='test_user',
                                         email='test@email.com')
    return builder.build()


@pytest.fixture
def denied_user():
    builder = RequestBuilder().with_args(request_type='qprove_user_request',
                                         username='denied_user',
                                         email='test2@email.com')
    return builder.build()


@pytest.mark.asyncio
async def test_user_handler_wrong_event(aprove_user_handler, wrong_event):
    loop = asyncio.get_running_loop()
    result = await aprove_user_handler.handle(wrong_event, loop)
    assert result is False


@pytest.mark.asyncio
async def test_user_handler_proper_event(aprove_user_handler,
                                         aproved_user,
                                         mocker):
    loop = asyncio.get_running_loop()
    original = aprove_user_handler.process_request
    aprove_user_handler.process_request = mocker.AsyncMock()
    result = await aprove_user_handler.handle(aproved_user, loop)
    assert result is True
    aprove_user_handler.process_request = original


@pytest.mark.asyncio
async def test_aprove_user_successfull_save_record_to_db(aprove_user_handler,
                                                         aproved_user,
                                                         status_success,
                                                         mocker):
    writer = mocker.AsyncMock()
    aprove_user_handler.connect_to_server.return_value = (status_success,
                                                          writer)
    await aprove_user_handler.process_request(aproved_user)
    aprove_user_handler.send_email.assert_called_with(aproved_user.username,
                                                      aproved_user.email,
                                                      True)
    record = {'username': aproved_user.username, 'request_result': 'aproved'}
    serialized_record = json.dumps(record) + '\n'
    writer.write.assert_called_with(serialized_record.encode())


@pytest.mark.asyncio
async def test_aprove_user_failed_save_record_to_db(aprove_user_handler,
                                                    aproved_user,
                                                    status_failed,
                                                    mocker):
    writer = mocker.AsyncMock()
    aprove_user_handler.connect_to_server.return_value = (status_failed,
                                                          writer)
    await aprove_user_handler.process_request(aproved_user)
    aprove_user_handler.send_email.assert_not_called()
    record = {'username': aproved_user.username, 'request_result': 'aproved'}
    serialized_record = json.dumps(record) + '\n'
    writer.write.assert_called_with(serialized_record.encode())


@pytest.mark.asyncio
async def test_deny_user_successfull_save_record_to_db(aprove_user_handler,
                                                       denied_user,
                                                       status_success,
                                                       mocker):
    writer = mocker.AsyncMock()
    aprove_user_handler.connect_to_server.return_value = (status_success,
                                                          writer)
    await aprove_user_handler.process_request(denied_user)
    aprove_user_handler.send_email.assert_called_with(denied_user.username,
                                                      denied_user.email,
                                                      False)
    record = {'username': denied_user.username, 'request_result': 'denied'}
    serialized_record = json.dumps(record) + '\n'
    writer.write.assert_called_with(serialized_record.encode())


@pytest.mark.asyncio
async def test_deny_user_falied_to_save_to_db(aprove_user_handler,
                                              denied_user,
                                              status_failed,
                                              mocker):
    writer = mocker.AsyncMock()
    aprove_user_handler.connect_to_server.return_value = (status_failed,
                                                          writer)
    await aprove_user_handler.process_request(denied_user)
    aprove_user_handler.send_email.assert_not_called()
    record = {'username': denied_user.username, 'request_result': 'denied'}
    serialized_record = json.dumps(record) + '\n'
    writer.write.assert_called_with(serialized_record.encode())


# -----------------------------------------------
# ------------ Test Video Request Handler -------
# -----------------------------------------------

@pytest.fixture
def video_request_handler(mocker):
    handler = VideoRequestHandler
    handler.connect_to_server = mocker.AsyncMock()
    return handler


@pytest.fixture
def proper_video_request():
    video_name = \
        camera_name \
        + '/' \
        + test_video_name \
        + '/' \
        + test_video_name \
        + 'T' \
        + test_time
    request_video_name = \
        test_video_name \
        + 'T' \
        + test_time \
        + '|' \
        + camera_name
    builder = RequestBuilder().with_args(
        request_type='video_request',
        video_name=request_video_name)
    full_video_name = SAVE_PATH / (video_name + '.mp4')
    if not os.path.isdir(SAVE_PATH / (camera_name
                                      + '/'
                                      + test_video_name
                                      + '/')):
        os.mkdir(SAVE_PATH / (camera_name + '/'))
        os.mkdir(SAVE_PATH / (camera_name + '/' + test_video_name + '/'))
    with open(full_video_name, 'wb') as test_video:
        test_video.write(bytes(10000))
    return builder.build()


@pytest.fixture
def wrong_video_request():
    builder = RequestBuilder().with_args(request_type='video_request',
                                         video_name='wrong_video|test_camera')
    return builder.build()


@pytest.mark.asyncio
async def test_video_handler_wrong_event(video_request_handler, wrong_event):
    loop = asyncio.get_running_loop()
    result = await video_request_handler.handle(wrong_event, loop)
    assert result is False


@pytest.mark.asyncio
async def test_video_handler_proper_event(video_request_handler,
                                          proper_video_request,
                                          mocker):
    loop = asyncio.get_running_loop()
    original = video_request_handler.process_request
    video_request_handler.process_request = mocker.AsyncMock()
    result = await video_request_handler.handle(proper_video_request, loop)
    assert result is True
    video_request_handler.process_request = original


@pytest.mark.asyncio
async def test_send_video(video_request_handler,
                          proper_video_request,
                          mocker):
    builder = RequestBuilder().with_args(
        request_type='video_response',
        video_name=proper_video_request.video_name,
        video_size=10000)
    excpected_request = builder.build()
    reader = mocker.AsyncMock()
    writer = mocker.AsyncMock()
    video_request_handler.connect_to_server.return_value = (reader, writer)
    await video_request_handler.process_request(proper_video_request)
    video_request_handler \
        .connect_to_server.assert_called_with(excpected_request)
    writer.write.assert_called_with(bytes(10000))
    video_name = \
        camera_name \
        + '/' \
        + test_video_name \
        + '/' \
        + test_video_name \
        + 'T' \
        + test_time
    os.remove(SAVE_PATH / (video_name + '.mp4'))
    os.rmdir(SAVE_PATH / (camera_name + '/' + test_video_name + '/'))
    os.rmdir(SAVE_PATH / (camera_name + '/'))


@pytest.mark.asyncio
async def test_failed_to_find_video(video_request_handler,
                                    wrong_video_request,
                                    mocker):
    builder = RequestBuilder().with_args(
        request_type='video_response',
        video_name=wrong_video_request.video_name,
        video_size=0)
    excpected_request = builder.build()
    reader = mocker.AsyncMock()
    writer = mocker.AsyncMock()
    video_request_handler.connect_to_server.return_value = (reader, writer)
    await video_request_handler.process_request(wrong_video_request)
    video_request_handler \
        .connect_to_server.assert_called_with(excpected_request)


# -----------------------------------------------
# ------------ Test Stream Request Handler ------
# -----------------------------------------------

@pytest.fixture
def stream_request_handler(mocker):
    handler = StreamHandler
    return handler


@pytest.fixture
def proper_stream_request():
    builder = RequestBuilder().with_args(request_type='stream_request',
                                         camera_name='test_camera')
    return builder.build()


@pytest.fixture
def stream_manager(mocker):
    manager = VideoStreamManager()
    manager.requesters = mocker.AsyncMock()
    return manager


@pytest.mark.asyncio
async def test_stream_handler_wrong_event(stream_request_handler,
                                          wrong_event):
    loop = asyncio.get_running_loop()
    result = await stream_request_handler.handle(wrong_event, loop)
    assert result is False


@pytest.mark.asyncio
async def test_stream_handler_proper_event(stream_request_handler,
                                           proper_stream_request,
                                           mocker):
    loop = asyncio.get_running_loop()
    original = stream_request_handler.process_request
    stream_request_handler.process_request = mocker.AsyncMock()
    result = await stream_request_handler.handle(proper_stream_request, loop)
    assert result is True
    stream_request_handler.process_request = original


@pytest.mark.asyncio
async def test_put_request_to_queue(stream_request_handler,
                                    proper_stream_request,
                                    stream_manager):
    await stream_request_handler.process_request(proper_stream_request)
    stream_manager.requesters.put.assert_called_with(proper_stream_request)
