import pytest
from ..handlers import SignalHandler
from ..camera_utils import ServerRequest

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
def new_video_record_request():
    return ServerRequest(request_type='new_record', db_record='test_record')


@pytest.fixture
def new_camera_record():
    return ServerRequest(request_type='new_record', camera_name='test_camera')


@pytest.mark.asyncio
async def test_wrong_request_for_new_record_handler(wrong_request):
    pass


@pytest.mark.asyncio
async def test_process_new_video_record(new_video_record_request):
    pass


@pytest.mark.asyncio
async def test_process_new_camera_record(new_camera_record):
    pass
