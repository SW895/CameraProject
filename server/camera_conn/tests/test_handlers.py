import pytest
from ..handlers import (SignalHandler,
                        NewRecordHandler,
                        VideoStreamRequestHandler,
                        VideoStreamResponseHandler,)
from ..camera_utils import ServerRequest
from ..db import NewVideoRecord, CameraRecord

pytest_plugins = ('pytest_asyncio', )


@pytest.fixture
def wrong_request():
    return ServerRequest(request_type='wrong_request')


# -----------------------------------------------
# ------------ Test Signal Handler --------------
# -----------------------------------------------

@pytest.fixture
def signal_request(mocker):
    request = ServerRequest(request_type='signal')
    request.writer = mocker.AsyncMock()
    return request


@pytest.fixture
def test_signal():
    return ServerRequest(request_type='test_signal')


@pytest.mark.asyncio
async def test_wrong_request_for_signal_handler(wrong_request):
    result = await SignalHandler.handle(wrong_request)
    assert result is None


@pytest.mark.asyncio
async def test_proper_request_lost_connection(signal_request, mocker):
    original = SignalHandler.process_signals
    mock = mocker.AsyncMock(side_effect=ConnectionResetError)
    SignalHandler.process_signals = mock
    result = await SignalHandler.handle(signal_request)
    assert result is True
    SignalHandler.process_signals = original


@pytest.mark.asyncio
async def test_process_signal(signal_request, test_signal):
    signal_request.writer.write.side_effect = None
    SignalHandler.connection = signal_request
    await SignalHandler.signal_queue.put(test_signal)
    await SignalHandler.process_signals()
    excpected_result = (test_signal.serialize() + '\n').encode()
    signal_request.writer.write.assert_called_once_with(excpected_result)
    signal_request.writer.drain.assert_awaited_once()


# -----------------------------------------------
# ------------ New Record Handler ---------------
# -----------------------------------------------


@pytest.fixture
def new_record_request():
    return ServerRequest(request_type='new_record')


@pytest.fixture
def new_video_record_request(mocker):
    request = ServerRequest(request_type='new_record',
                            db_record='test_record')
    request.writer = mocker.AsyncMock()
    request.reader = mocker.AsyncMock()
    request.reader.read.return_value = b""
    return request


@pytest.fixture
def new_camera_record(mocker):
    request = ServerRequest(request_type='new_record',
                            camera_name='test_camera')
    request.writer = mocker.AsyncMock()
    request.reader = mocker.AsyncMock()
    request.reader.read.return_value = b""
    return request


@pytest.fixture
def new_record_handler(mocker):
    handler = NewRecordHandler()
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
    assert new_record_handler.record_handler is NewVideoRecord
    assert result is True


@pytest.mark.asyncio
async def test_close_connection_for_video_record(new_video_record_request,
                                                 new_record_handler):
    result = await new_record_handler.handle(new_video_record_request)
    new_video_record_request.reader.read.assert_called()
    new_video_record_request.writer.close.assert_called()
    assert result is True


@pytest.mark.asyncio
async def test_set_camera_record_save_mathod(new_camera_record,
                                             new_record_handler):
    result = await new_record_handler.handle(new_camera_record)
    assert new_record_handler.record_handler is CameraRecord
    assert result is True


@pytest.mark.asyncio
async def test_close_connection_for_camera_record(new_camera_record,
                                                  new_record_handler):
    result = await new_record_handler.handle(new_camera_record)
    new_camera_record.reader.read.assert_called()
    new_camera_record.writer.close.assert_called()
    assert result is True


@pytest.mark.asyncio
async def test_save_called(new_camera_record, mocker):
    NewRecordHandler.save = mocker.AsyncMock()
    result = await NewRecordHandler.handle(new_camera_record)
    NewRecordHandler.save.assert_called()
    assert result is True


# -----------------------------------------------
# ------------ VideoStream request --------------
# -----------------------------------------------

@pytest.fixture
def video_stream_request():
    return ServerRequest(request_type='stream_request')


@pytest.fixture
def video_stream_request_handler(mocker):
    handler = VideoStreamRequestHandler()
    handler.manager = mocker.AsyncMock()
    return handler


@pytest.mark.asyncio
async def test_video_stream_request_handler_wrong_request(wrong_request):
    result = await VideoStreamRequestHandler.handle(wrong_request)
    assert result is None


@pytest.mark.asyncio
async def test_video_stream_request_handler_request(video_stream_request,
                                                    video_stream_request_handler):
    result = await VideoStreamRequestHandler.handle(video_stream_request)
    video_stream_request_handler.manager.responses.put.assert_awaite()
    assert result is True
