import pytest
import sys
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(base_dir))
from handlers import (SignalHandler,
                      NewRecordHandler,
                      VideoStreamRequestHandler,
                      VideoStreamResponseHandler,
                      VideoRequestHandler,
                      VideoResponseHandler,
                      AproveUserRequestHandler)
from cam_server import RequestBuilder
from db import NewVideoRecord, CameraRecord, UserRecord

pytest_plugins = ('pytest_asyncio', )


@pytest.fixture
def wrong_request():
    builder = RequestBuilder().with_args(request_type='wrong_request')
    return builder.build()


# -----------------------------------------------
# ------------ Test Signal Handler --------------
# -----------------------------------------------

@pytest.fixture
def signal_request(mocker):
    writer = mocker.AsyncMock()
    builder = RequestBuilder().with_args(request_type='signal',
                                         writer=writer)
    return builder.build()


@pytest.fixture
def test_signal():
    builder = RequestBuilder().with_args(request_type='test_signal')
    return builder.build()


@pytest.fixture
def signal_handler(mocker):
    handler = SignalHandler
    handler.manager = mocker.AsyncMock()
    return handler


@pytest.mark.asyncio
async def test_wrong_request_for_signal_handler(wrong_request,
                                                signal_handler):
    result = await signal_handler.handle(wrong_request)
    assert result is None


@pytest.mark.asyncio
async def test_put_connection_to_signal_collector(signal_handler,
                                                  signal_request):
    result = await signal_handler.handle(signal_request)
    assert result is True
    signal_handler.manager.client_queue.put.assert_called_with(signal_request)


# -----------------------------------------------
# ------------ New Record Handler ---------------
# -----------------------------------------------

@pytest.fixture
def new_video_record_request(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    reader.read.return_value = b"1"
    builder = RequestBuilder().with_args(request_type='new_video_record',
                                         writer=writer,
                                         reader=reader,
                                         record_size=1)
    return builder.build()


@pytest.fixture
def new_camera_record(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    reader.read.return_value = b"1"
    builder = RequestBuilder().with_args(request_type='new_camera_record',
                                         writer=writer,
                                         reader=reader,
                                         record_size=1)
    return builder.build()


@pytest.fixture
def aprove_user_response(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    reader.read.return_value = b"1"
    builder = RequestBuilder().with_args(request_type='aprove_user_response',
                                         writer=writer,
                                         reader=reader,
                                         record_size=1)
    return builder.build()


@pytest.fixture
def new_record_handler(mocker):
    handler = NewRecordHandler
    handler.save = mocker.AsyncMock()
    return handler


@pytest.mark.asyncio
async def test_wrong_request_for_new_record_handler(wrong_request):
    result = await NewRecordHandler.handle(wrong_request)
    assert result is None


@pytest.mark.asyncio
async def test_set_new_video_record_save_method(new_video_record_request,
                                                new_record_handler):
    result = await new_record_handler.handle(new_video_record_request)
    assert type(new_record_handler.get_handler()) is NewVideoRecord
    assert result is True


@pytest.mark.asyncio
async def test_set_camera_record_save_mathod(new_camera_record,
                                             new_record_handler):
    result = await new_record_handler.handle(new_camera_record)
    assert type(new_record_handler.get_handler()) is CameraRecord
    assert result is True


@pytest.mark.asyncio
async def test_set_user_record_save_mathod(aprove_user_response,
                                           new_record_handler):
    result = await new_record_handler.handle(aprove_user_response)
    assert type(new_record_handler.get_handler()) is UserRecord
    assert result is True


@pytest.mark.asyncio
async def test_read_data_from_connection(new_video_record_request,
                                         new_record_handler):
    result = await new_record_handler.handle(new_video_record_request)
    new_video_record_request.reader.read.assert_called()
    assert result is True


@pytest.mark.asyncio
async def test_save_called(new_camera_record, new_record_handler):
    result = await new_record_handler.handle(new_camera_record)
    new_record_handler.save.assert_called()
    assert result is True


@pytest.mark.asyncio
async def test_queue_record_put(new_camera_record, new_record_handler):
    result = await new_record_handler.handle(new_camera_record)
    record = await new_record_handler.get_handler().save_queue.get()
    assert result is True
    import json
    assert record == json.loads(new_camera_record.reader
                                                 .read
                                                 .return_value
                                                 .decode())


# -----------------------------------------------
# ------------ VideoStream request --------------
# -----------------------------------------------

@pytest.fixture
def video_stream_request():
    builder = RequestBuilder().with_args(request_type='stream_request')
    return builder.build()


@pytest.fixture
def video_stream_request_handler(mocker):
    handler = VideoStreamRequestHandler()
    handler.manager.requesters = mocker.AsyncMock()
    return handler


@pytest.mark.asyncio
async def test_video_stream_request_handler_wrong_request(
    wrong_request,
    video_stream_request_handler
):
    result = await video_stream_request_handler.handle(wrong_request)
    assert result is None


@pytest.mark.asyncio
async def test_video_stream_request_handler_request(
    video_stream_request,
    video_stream_request_handler
):
    result = await video_stream_request_handler.handle(video_stream_request)
    video_stream_request_handler.manager \
        .requesters \
        .put \
        .assert_called_with(video_stream_request)
    assert result is True


# -----------------------------------------------
# ------------ VideoStream response -------------
# -----------------------------------------------

@pytest.fixture
def video_stream_response():
    builder = RequestBuilder().with_args(request_type='stream_response')
    return builder.build()


@pytest.fixture
def video_stream_response_handler(mocker):
    handler = VideoStreamResponseHandler()
    handler.manager.responses = mocker.AsyncMock()
    return handler


@pytest.mark.asyncio
async def test_video_stream_response_handler_wrong_request(
    wrong_request,
    video_stream_response_handler
):
    result = await video_stream_response_handler.handle(wrong_request)
    assert result is None


@pytest.mark.asyncio
async def test_video_stream_response_handler_request(
    video_stream_response,
    video_stream_response_handler
):
    result = await video_stream_response_handler.handle(video_stream_response)
    video_stream_response_handler.manager \
        .responses \
        .put \
        .assert_called_with(video_stream_response)
    assert result is True


# -----------------------------------------------
# ------------ Video Request --------------------
# -----------------------------------------------

@pytest.fixture
def video_request():
    builder = RequestBuilder().with_args(request_type='video_request')
    return builder.build()


@pytest.fixture
def video_request_handler(mocker):
    handler = VideoRequestHandler()
    handler.manager.requesters = mocker.AsyncMock()
    return handler


@pytest.mark.asyncio
async def test_video_request_handler_wrong_request(wrong_request,
                                                   video_request_handler):
    result = await video_request_handler.handle(wrong_request)
    assert result is None


@pytest.mark.asyncio
async def test_video_request_handler_request(video_request,
                                             video_request_handler):
    result = await video_request_handler.handle(video_request)
    video_request_handler.manager \
        .requesters \
        .put \
        .assert_called_with(video_request)
    assert result is True


# -----------------------------------------------
# ------------ Video Response -------------------
# -----------------------------------------------

@pytest.fixture
def video_response(mocker):
    reader = mocker.AsyncMock()
    writer = mocker.AsyncMock()
    builder = RequestBuilder().with_args(request_type='video_response',
                                         video_name='test_video',
                                         video_size=65000,
                                         reader=reader,
                                         writer=writer)
    return builder.build()


@pytest.fixture
def video_response_handler(mocker):
    handler = VideoResponseHandler
    handler.save_file = mocker.AsyncMock()
    handler.manager.responses = mocker.AsyncMock()
    return handler


@pytest.mark.asyncio
async def test_video_response_handler_wrong_request(wrong_request,
                                                    video_response_handler):
    result = await video_response_handler.handle(wrong_request)
    assert result is None


@pytest.mark.asyncio
async def test_video_file_zero_size(video_response,
                                    video_response_handler):
    video_response.video_size = 0
    result = await video_response_handler.handle(video_response)
    builder = RequestBuilder().with_args(request_type='video_reponse',
                                         request_result='failure',
                                         video_name=video_response.video_name)
    expected_call = builder.build()
    video_response_handler.manager \
        .responses \
        .put \
        .assert_called_with(expected_call)
    assert result is True


@pytest.mark.asyncio
async def test_fail_to_receive_video(video_response,
                                     video_response_handler):
    video_response.video_size = 65000
    video_response.reader.read.return_value = b""
    result = await video_response_handler.handle(video_response)
    builder = RequestBuilder().with_args(request_type='video_reponse',
                                         request_result='failure',
                                         video_name=video_response.video_name)
    expected_call = builder.build()
    video_response_handler.manager \
        .responses \
        .put \
        .assert_called_with(expected_call)
    assert result is True


@pytest.mark.asyncio
async def test_successfully_receive_video(video_response,
                                          video_response_handler):
    video_response.video_size = 65000
    video_response.reader.read.return_value = bytes(video_response.video_size)

    result = await video_response_handler.handle(video_response)
    builder = RequestBuilder().with_args(request_type='video_reponse',
                                         request_result='success',
                                         video_name=video_response.video_name)
    expected_call = builder.build()
    video_response_handler.manager \
        .responses \
        .put \
        .assert_called_with(expected_call)
    assert result is True


# -----------------------------------------------
# ------------ Aprove User Request --------------
# -----------------------------------------------

@pytest.fixture
def aprove_request(mocker):
    writer = mocker.AsyncMock()
    builder = RequestBuilder().with_args(request_type='aprove_user_request',
                                         writer=writer)
    return builder.build()


@pytest.fixture
def aprove_user_request_handler(mocker):
    handler = AproveUserRequestHandler
    handler.signal.signal_queue = mocker.AsyncMock()
    return handler


@pytest.mark.asyncio
async def test_aprove_user_request_handler_wrong_request(
    wrong_request,
    aprove_user_request_handler
):
    result = await aprove_user_request_handler.handle(wrong_request)
    assert result is None


@pytest.mark.asyncio
async def test_aprove_user_request_handler_request(
    aprove_request,
    aprove_user_request_handler
):
    result = await aprove_user_request_handler.handle(aprove_request)
    aprove_user_request_handler.signal \
        .signal_queue \
        .put \
        .assert_called_with(aprove_request)
    assert result is True
