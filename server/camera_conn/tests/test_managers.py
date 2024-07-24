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

    def __call__(self, buffer=0):
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
    manager.loop = mocker.AsyncMock()
    manager.get_active_camera_list = mocker.AsyncMock()
    manager.get_active_camera_list \
        .return_value = [['test_camera', 'test_user']]
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
    request.reader.read.side_effect = ErrorAfter(
                                                limit=1,
                                                return_value=b'111')
    return request


@pytest.fixture
def stream_channel():
    channel = StreamChannel('test_camera')
    channel.source_timeout = 0.5
    return channel


@pytest.mark.asyncio
async def test_get_requester_with_key_error(videostream_manager,
                                            mocker):
    videostream_manager.stream_channels = {}
    with pytest.raises(CallableExhausted):
        await videostream_manager.process_requesters()
    videostream_manager.get_active_camera_list.assert_called()


@pytest.mark.asyncio
async def test_get_requester_without_error(videostream_manager,
                                           mocker):
    videostream_manager.stream_channels = {'test_camera': 'test'}
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
    videostream_manager.stream_channels = {'test_camera':
                                           StreamChannel('test_camera')}
    videostream_manager.stream_channels['test_camera']\
        .source_queue = mocker.AsyncMock()
    with pytest.raises(CallableExhausted):
        await videostream_manager.process_responses()
    videostream_manager.stream_channels['test_camera'] \
        .source_queue \
        .put \
        .assert_called_with(stream_response)


@pytest.mark.asyncio
async def test_update_camera_list(videostream_manager):
    videostream_manager.stream_channels = {}
    await videostream_manager.update_stream_channels()
    assert videostream_manager.stream_channels['test_camera']
    assert videostream_manager.stream_channels['test_camera'] \
           .camera_name == 'test_camera'


@pytest.mark.asyncio
async def test_run_channel_with_no_consumers(stream_channel,
                                             videostream_manager,
                                             stream_requester):
    stream_channel.consumer_list = []
    await videostream_manager.run_channel(stream_channel, stream_requester)
    videostream_manager.loop \
        .create_task \
        .assert_called()
    assert stream_channel.consumer_list


@pytest.mark.asyncio
async def test_run_channel_with_consumers(stream_channel,
                                          videostream_manager,
                                          stream_requester):
    stream_channel.consumer_list = ['test_consumer']
    await videostream_manager.run_channel(stream_channel, stream_requester)
    videostream_manager.loop \
        .create_task \
        .assert_not_called()
    assert stream_channel.consumer_list == ['test_consumer', stream_requester]


# -----------------------------------------------
# ------------ Stream Channel -------------------
# -----------------------------------------------

@pytest.mark.asyncio
async def test_add_consumer(stream_requester, stream_channel):
    stream_channel.consumer_list = []
    await stream_channel.add_consumer(stream_requester)
    assert stream_channel.consumer_list == [stream_requester]


@pytest.mark.asyncio
async def test_timeout_exit_if_no_source(stream_channel):
    stream_channel.consumer_list = []
    stream_channel.source = None
    result = await stream_channel.run_channel()
    assert result == 100


@pytest.mark.asyncio
async def test_proper_clean_up_with_no_source(stream_channel,
                                              stream_requester, mocker):
    stream_channel.source_queue = mocker.AsyncMock()
    stream_channel.source_queue.get.side_effect = TimeoutError
    await stream_channel.add_consumer(stream_requester)
    result = await stream_channel.run_channel()
    assert result == 100
    assert stream_channel.consumer_list == []
    assert stream_channel.task is None
    assert stream_channel.source is None
    stream_requester.writer.close.assert_called()


@pytest.mark.asyncio
async def test_send_all_called(stream_channel,
                               stream_requester,
                               stream_response):

    await stream_channel.source_queue.put(stream_response)
    await stream_channel.add_consumer(stream_requester)
    result = await stream_channel.run_channel()
    assert result == 200
    stream_requester.writer.write.assert_called()


@pytest.mark.asyncio
async def test_remove_consumer(stream_channel,
                               stream_requester,
                               stream_response):
    stream_requester.writer.write.side_effect = ConnectionResetError
    await stream_channel.source_queue.put(stream_response)
    await stream_channel.add_consumer(stream_requester)
    result = await stream_channel.run_channel()
    assert result == 200
    assert stream_channel.consumer_list == []


@pytest.mark.asyncio
async def test_proper_clean_up(stream_channel,
                               stream_requester,
                               stream_response):
    stream_channel.source = stream_response
    stream_channel.task = 'test'
    await stream_channel.add_consumer(stream_requester)
    await stream_channel.clean_up()
    assert stream_channel.source is None
    assert stream_channel.consumer_list == []
    assert stream_channel.task is None

# -----------------------------------------------
# ------------ Video Request manager ------------
# -----------------------------------------------
"""
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