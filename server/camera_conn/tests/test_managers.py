import pytest
from camera_conn.cam_server import RequestBuilder
from camera_conn.managers import (VideoRequestManager,
                                  VideoStreamManager,
                                  VideoRequest,
                                  StreamChannel,
                                  SignalCollector,
                                  Client)
from camera_conn.camera_utils import (ErrorAfter,
                                      CallableExhausted)


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
        .return_value = [('test_camera', 'test_user')]
    manager.requesters.get.side_effect = ErrorAfter(
                                            limit=1,
                                            return_value=stream_requester)
    manager.responses.get.side_effect = ErrorAfter(
                                            limit=1,
                                            return_value=stream_response)
    return manager


@pytest.fixture
def stream_requester(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    builder = RequestBuilder().with_args(request_type='stream_request',
                                         camera_name='test_camera',
                                         reader=reader,
                                         writer=writer)
    return builder.build()


@pytest.fixture
def stream_response(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    reader.read.side_effect = ErrorAfter(limit=1,
                                         return_value=b'111')
    builder = RequestBuilder().with_args(request_type='stream_response',
                                         camera_name='test_camera',
                                         reader=reader,
                                         writer=writer)
    return builder.build()


@pytest.fixture
def stream_channel():
    channel = StreamChannel('test_camera')
    channel.source_timeout = 0.05
    return channel


@pytest.mark.asyncio
async def test_get_requester_with_key_error(videostream_manager):
    videostream_manager.stream_channels = {}
    with pytest.raises(CallableExhausted):
        await videostream_manager.process_requesters()
    videostream_manager.get_active_camera_list.assert_called()


@pytest.mark.asyncio
async def test_get_requester_without_error(videostream_manager):
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
                                          stream_channel,
                                          mocker):
    videostream_manager.stream_channels = {'test_camera': stream_channel}
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
    assert result == 'TimeoutError'


@pytest.mark.asyncio
async def test_proper_clean_up_with_no_source(stream_channel,
                                              stream_requester,
                                              mocker):
    stream_channel.source_queue = mocker.AsyncMock()
    stream_channel.source_queue.get.side_effect = TimeoutError
    await stream_channel.add_consumer(stream_requester)
    result = await stream_channel.run_channel()
    assert result == 'TimeoutError'
    assert stream_channel.consumer_list == []
    assert stream_channel.task is None
    assert stream_channel.source is None
    stream_requester.writer.close.assert_called()


@pytest.mark.asyncio
async def test_data_sended_to_consumers(stream_channel,
                                        stream_requester,
                                        stream_response):

    await stream_channel.source_queue.put(stream_response)
    await stream_channel.add_consumer(stream_requester)
    result = await stream_channel.run_channel()
    assert result is True
    stream_requester.writer.write.assert_called()


@pytest.mark.asyncio
async def test_remove_consumer(stream_channel, stream_requester, mocker):
    stream_requester.writer.write = mocker.Mock(side_effect=BrokenPipeError)
    await stream_channel.add_consumer(stream_requester)
    await stream_channel.send_to_all(b'100')
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

@pytest.fixture
def videorequest_manager(mocker, video_request, video_response):
    manager = VideoRequestManager()
    manager.loop = mocker.AsyncMock()
    manager.requesters = mocker.AsyncMock()
    manager.requesters.get.side_effect = ErrorAfter(limit=1,
                                                    return_value=video_request)
    manager.responses = mocker.AsyncMock()
    manager.responses.get.side_effect = ErrorAfter(limit=1,
                                                   return_value=video_response)
    manager.send_request = mocker.AsyncMock()
    return manager


@pytest.fixture
def video_request(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    builder = RequestBuilder().with_args(request_type='video_request',
                                         video_name='test_video',
                                         reader=reader,
                                         writer=writer)
    return builder.build()


@pytest.fixture
def video_response(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    builder = RequestBuilder().with_args(request_type='video_response',
                                         video_size=1000,
                                         video_name='test_video',
                                         request_result='failure',
                                         reader=reader,
                                         writer=writer)
    return builder.build()


@pytest.fixture
def video_request_object(mocker, video_response):
    videorequest = VideoRequest(video_name='test_video')
    videorequest.response_queue = mocker.AsyncMock()
    videorequest.response_queue.get.return_value = video_response
    return videorequest


@pytest.mark.asyncio
async def test_create_new_video_request(videorequest_manager, video_request):
    with pytest.raises(CallableExhausted):
        await videorequest_manager.process_requesters()
    assert videorequest_manager.requested_videos == \
        {video_request.video_name: VideoRequest(video_request.video_name)}
    videorequest_manager.send_request.assert_called_with(video_request)


@pytest.mark.asyncio
async def test_add_requester_to_existing_video_request(videorequest_manager,
                                                       video_request):
    videorequest_manager.requested_videos[video_request.video_name] = \
        VideoRequest(video_request.video_name)
    with pytest.raises(CallableExhausted):
        await videorequest_manager.process_requesters()
    assert videorequest_manager.requested_videos[video_request.video_name] \
        .requesters[0] == video_request
    videorequest_manager.send_request.assert_not_called()


@pytest.mark.asyncio
async def test_failed_response(videorequest_manager):
    with pytest.raises(CallableExhausted):
        try:
            await videorequest_manager.process_responses()
        except KeyError:
            pytest.fail('KeyError not handled')


@pytest.mark.asyncio
async def test_success_response(videorequest_manager,
                                video_response,
                                mocker):
    record = VideoRequest(video_response.video_name)
    record.response_queue = mocker.AsyncMock()
    videorequest_manager.requested_videos[video_response.video_name] = record
    with pytest.raises(CallableExhausted):
        await videorequest_manager.process_responses()
    record.response_queue.put.assert_called_with(video_response)


@pytest.mark.asyncio
async def test_remove_expired_requests(videorequest_manager, mocker):
    import asyncio
    asyncio.sleep = mocker.AsyncMock()
    asyncio.sleep.side_effect = ErrorAfter(limit=1, return_value=None)
    finished_task = VideoRequest('finished_task')
    finished_task.task_done = True
    active_task = VideoRequest('active_task')
    videorequest_manager.requested_videos = {'finished_task': finished_task,
                                             'active_task': active_task}
    with pytest.raises(CallableExhausted):
        await videorequest_manager.garb_collector()
    assert videorequest_manager.requested_videos['active_task']
    assert len(videorequest_manager.requested_videos.keys()) == 1


# -----------------------------------------------
# ------------ Video Request --------------------
# -----------------------------------------------

@pytest.mark.asyncio
async def test_add_requester(video_request_object, video_request):
    await video_request_object.add_requester(video_request)
    assert video_request_object.requesters[0] == video_request


@pytest.mark.asyncio
async def test_timeout_falure(video_request_object, video_request):
    await video_request_object.add_requester(video_request)
    video_request_object.response_queue.get.side_effect = TimeoutError
    await video_request_object.process_request()
    response = 'timeout_error'
    assert video_request_object.response == response
    video_request.writer.write.assert_called()
    video_request.writer.write.assert_called_with(response.encode())


@pytest.mark.asyncio
async def test_send_response(video_request_object,
                             video_request,
                             video_response):
    await video_request_object.add_requester(video_request)
    video_request_object.response_queue.get.side_effect = None
    await video_request_object.process_request()
    response = video_response.request_result
    assert video_request_object.response == response
    video_request.writer.write.assert_called_with(response.encode())


# -----------------------------------------------
# ------------ Signal Collector -----------------
# -----------------------------------------------

@pytest.fixture
def signal_collector(mocker, client_request, custom_signal):
    manager = SignalCollector()
    manager.loop = mocker.AsyncMock()
    manager.requesters = mocker.AsyncMock()
    manager.requesters.get.side_effect = ErrorAfter(
                                            limit=1,
                                            return_value=client_request)
    manager.responses = mocker.AsyncMock()
    manager.responses.get.side_effect = ErrorAfter(
                                            limit=1,
                                            return_value=custom_signal)
    return manager


@pytest.fixture
def client_request(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    builder = RequestBuilder().with_args(request_type='signal',
                                         ident='new',
                                         reader=reader,
                                         writer=writer)
    request = builder.build()
    request.client_id = 'test_client'
    return request


@pytest.fixture
def old_client(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    builder = RequestBuilder().with_args(request_type='signal',
                                         ident='old',
                                         reader=reader,
                                         writer=writer)
    request = builder.build()
    request.client_id = 'test_client'
    return request


@pytest.fixture
def dead_client(mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    builder = RequestBuilder().with_args(request_type='signal',
                                         ident='old',
                                         reader=reader,
                                         writer=writer)
    request = builder.build()
    request.client_id = 'dead_client'
    return request


@pytest.fixture
def custom_signal():
    builder = RequestBuilder().with_args(request_type='any')
    signal = builder.build()
    signal.client_id = 'test_client'
    return signal


@pytest.fixture
def client(client_request, custom_signal, mocker):
    client = Client(client_request)
    client.signal_queue = mocker.AsyncMock()
    client.signal_queue.get.return_value = custom_signal
    return client


@pytest.mark.asyncio
async def test_create_new_client(signal_collector, client_request):
    with pytest.raises(CallableExhausted):
        await signal_collector.process_requesters()
    assert signal_collector.clients[client_request.client_id]
    assert signal_collector \
        .clients[client_request.client_id] \
        .client == client_request


@pytest.mark.asyncio
async def test_update_existing_client(signal_collector,
                                      client_request,
                                      old_client):
    signal_collector \
        .clients.update({old_client.client_id: Client(old_client)})
    with pytest.raises(CallableExhausted):
        await signal_collector.process_requesters()
    assert signal_collector \
        .clients[client_request.client_id] \
        .client \
        .ident == client_request.ident
    assert signal_collector.clients[client_request.client_id]
    assert signal_collector \
        .clients[client_request.client_id] \
        .client == client_request
    signal_collector.loop.create_task.assert_called()


@pytest.mark.asyncio
async def test_get_signal_for_non_existing_client(signal_collector):
    with pytest.raises(CallableExhausted):
        try:
            await signal_collector.process_responses()
        except KeyError:
            pytest.fail('KeyError not handled')


@pytest.mark.asyncio
async def test_get_signal(signal_collector, client_request, custom_signal):
    signal_collector \
        .clients \
        .update({client_request.client_id: Client(client_request)})
    with pytest.raises(CallableExhausted):
        await signal_collector.process_responses()
    result = await signal_collector \
        .clients[client_request.client_id] \
        .signal_queue \
        .get()
    assert result == custom_signal


@pytest.mark.asyncio
async def test_remove_expired_clients(signal_collector,
                                      client_request,
                                      dead_client,
                                      mocker):
    import asyncio
    asyncio.sleep = mocker.AsyncMock()
    asyncio.sleep.side_effect = ErrorAfter(limit=1, return_value=None)
    d_client = Client(dead_client)
    d_client.dead = True
    a_client = Client(client_request)
    signal_collector.clients = {dead_client.client_id: d_client,
                                client_request.client_id: a_client}
    with pytest.raises(CallableExhausted):
        await signal_collector.garb_collector()
    assert signal_collector.clients[client_request.client_id]
    assert len(signal_collector.clients.keys()) == 1


# -----------------------------------------------
# ------------ Client ---------------------------
# -----------------------------------------------

@pytest.mark.asyncio
async def test_proper_request_lost_connection(client, mocker):
    original = client.process_signals
    client.process_signals = mocker.AsyncMock(side_effect=ConnectionResetError)
    await client.handle_signals()
    client.client.writer.close.assert_called()
    client.process_signals = original


@pytest.mark.asyncio
async def test_process_signal(client, custom_signal):
    client.client.writer.write.side_effect = None

    await client.process_signals()
    excpected_result = (custom_signal.serialize()).encode()
    client.client.writer.write.assert_called_once_with(excpected_result)
    client.client.writer.drain.assert_awaited_once()
