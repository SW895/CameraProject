import pytest
from ..managers import (VideoRequestManager,
                        VideoStreamManager,
                        VideoRequest,
                        StreamChannel)
from ..camera_utils import ServerRequest


class ErrorAfter(object):
    '''
    Callable that will raise `CallableExhausted`
    exception after `limit` calls

    '''
    def __init__(self, limit, return_value):
        self.limit = limit
        self.calls = 0
        self.return_value = return_value

    def __call__(self):
        self.calls += 1
        if self.calls > self.limit:
            raise CallableExhausted
        return self.return_value


class CallableExhausted(Exception):
    pass


# -----------------------------------------------
# ------------ Video Stream manager -------------
# -----------------------------------------------

@pytest.fixture
def videostream_manager(mocker, stream_requester, stream_response):
    manager = VideoStreamManager()
    signal_handler = mocker.AsyncMock()
    manager.set_signal_handler(signal_handler)
    manager.requesters = mocker.AsyncMock()
    manager.responses = mocker.AsyncMock()
    manager.requesters.get.side_effect = ErrorAfter(
                                            limit=1,
                                            return_value=stream_requester)
    manager.responses.get.side_effect = ErrorAfter(
                                            limit=1,
                                            return_value=stream_response)
    return manager


@pytest.fixture
def stream_requester(mocker):
    request = ServerRequest(request_type='stream_request',
                            camera_name='test_camera')
    request.writer = mocker.AsyncMock()
    request.reader = mocker.AsyncMock()
    return request


@pytest.fixture
def stream_response(mocker):
    request = ServerRequest(request_type='stream_response',
                            camera_name='test_camera')
    request.writer = mocker.AsyncMock()
    request.reader = mocker.AsyncMock()
    return request


@pytest.mark.asyncio
async def test_get_requester_with_key_error(videostream_manager,
                                            mocker):
    videostream_manager.stream_channels = {}
    videostream_manager.update_stream_channels = mocker.AsyncMock()
    with pytest.raises(CallableExhausted):
        await videostream_manager.process_requesters()
    videostream_manager.update_stream_channels.assert_called()


@pytest.mark.asyncio
async def test_get_requester_without_error(videostream_manager,
                                           mocker):
    videostream_manager.stream_channels = {'test_camera': 'test'}
    videostream_manager.update_stream_channels = mocker.AsyncMock()
    videostream_manager.loop = mocker.AsyncMock()
    with pytest.raises(CallableExhausted):
        await videostream_manager.process_requesters()
    videostream_manager.loop.create_task.assert_called()


@pytest.mark.asyncio
async def test_get_response_with_key_error(videostream_manager):
    videostream_manager.stream_channels = {}
    with pytest.raises(CallableExhausted):
        try:
            await videostream_manager.process_responses()
        except KeyError:
            pytest.fail('KeyError not handled')


@pytest.mark.asyncio
async def test_get_response_without_error(videostream_manager,
                                          stream_response,
                                          mocker):
    videostream_manager.stream_channels = {'test_camera': StreamChannel('test_camera')}
    videostream_manager.stream_channels['test_camera']\
        .source_queue = mocker.AsyncMock()
    with pytest.raises(CallableExhausted):
        await videostream_manager.process_responses()
    videostream_manager.stream_channels['test_camera'] \
        .source_queue \
        .put \
        .assert_called_with(stream_response)


@pytest.mark.asyncio
async def test_update_camera_list(mocker):
    mocker.patch('camera_conn.managers.ActiveCamera', attribute='get_active_camera_list')


@pytest.mark.asyncio
async def test_run_channel_with_no_consumers():
    pass


@pytest.mark.asyncio
async def test_run_channel_with_consumers():
    pass


# -----------------------------------------------
# ------------ Stream Channel -------------------
# -----------------------------------------------
"""
@pytest.mark.asyncio
async def test_add_consumer():
    pass


@pytest.mark.asyncio
async def test_exit_if_no_source():
    pass


@pytest.mark.asyncio
async def test_call_clean_up():
    pass


@pytest.mark.asyncio
async def test_send_all_called():
    pass


@pytest.mark.asyncio
async def test_remove_consumer():
    pass


@pytest.mark.asyncio
async def test_proper_clean_up():
    pass


# -----------------------------------------------
# ------------ Video Request manager ------------
# -----------------------------------------------

@pytest.mark.asyncio
async def test_create_new_video_request():
    pass


@pytest.mark.asyncio
async def test_add_requester_to_video_request():
    pass


@pytest.mark.asyncio
async def test_failed_response():
    pass


@pytest.mark.asyncio
async def test_success_response():
    pass


@pytest.mark.asyncio
async def test_remove_expired_requests():
    pass


# -----------------------------------------------
# ------------ Video Request --------------------
# -----------------------------------------------

@pytest.mark.asyncio
async def test_add_requester():
    pass


@pytest.mark.asyncio
async def test_timeout_falure():
    pass


@pytest.mark.asyncio
async def test_send_response():
    pass
"""