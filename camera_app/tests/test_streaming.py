import pytest
import sys
import asyncio
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(base_dir))
from request_builder import RequestBuilder
from streaming import (
    VideoStream,
    VideoStreamManager,
)
from utils import (
    CallableExhausted,
    ErrorAfter
)


pytest_plugins = ('pytest_asyncio', )


# -----------------------------------------------
# ------------ Test Stream Manager --------------
# -----------------------------------------------

@pytest.fixture
def stream_requester():
    builder = RequestBuilder().with_args(request_type='stream_request',
                                         camera_name='test_camera')
    return builder.build()


@pytest.fixture
def bad_stream_requester():
    builder = RequestBuilder().with_args(request_type='stream_request',
                                         camera_name='aaa')
    return builder.build()


@pytest.fixture
def videostream_manager(videostream_channel, mocker):
    camera_name = 'test_camera'
    manager = VideoStreamManager()
    manager.set_event_loop(mocker.Mock())
    manager.cameras.update({camera_name: videostream_channel})
    return manager


@pytest.fixture
def videostream_channel(mocker):

    def make_worker():
        return

    test_frame = 'test_frame'
    worker = make_worker
    worker.videostream_frame = mocker.AsyncMock()
    worker.videostream_frame.get.side_effect = ErrorAfter(
        limit=1,
        return_value=test_frame.encode())
    channel = VideoStream(camera_worker=worker,
                          camera_name='test_camera')
    channel.connect_to_server = mocker.AsyncMock()
    return channel


@pytest.mark.asyncio
async def test_existing_camera(videostream_manager,
                               stream_requester,
                               mocker):
    videostream_manager.requesters = mocker.AsyncMock()
    videostream_manager.requesters.get.side_effect = ErrorAfter(
        limit=1,
        return_value=stream_requester)
    original = videostream_manager.run_channel
    videostream_manager.run_channel = mocker.AsyncMock()
    with pytest.raises(CallableExhausted):
        await videostream_manager.run_manager()
    videostream_manager.run_channel.assert_called()
    videostream_manager.run_channel = original


@pytest.mark.asyncio
async def test_non_existing_camera_camera(videostream_manager,
                                          bad_stream_requester,
                                          mocker):
    videostream_manager.requesters = mocker.AsyncMock()
    videostream_manager.requesters.get.side_effect = ErrorAfter(
        limit=1,
        return_value=bad_stream_requester)
    original = videostream_manager.run_channel
    videostream_manager.run_channel = mocker.AsyncMock()
    with pytest.raises(CallableExhausted):
        await videostream_manager.run_manager()
    videostream_manager.run_channel.assert_not_called()
    videostream_manager.run_channel = original


@pytest.mark.asyncio
async def test_cancel_task_if_channel_already_exists(
    videostream_manager,
    videostream_channel,
):
    videostream_channel.task = asyncio.Future()
    with pytest.raises(asyncio.CancelledError):
        await videostream_manager.run_channel(videostream_channel)
    assert videostream_channel.task.cancelled()


@pytest.mark.asyncio
async def test_run_new_channel(videostream_channel,
                               videostream_manager):
    await videostream_manager.run_channel(videostream_channel)
    videostream_manager.loop.create_task.assert_called()
    assert videostream_channel.task


# -----------------------------------------------
# ------------ Test Video Stream ----------------
# -----------------------------------------------

@pytest.mark.asyncio
async def test_stream_video(videostream_channel, mocker):
    writer = mocker.AsyncMock()
    reader = mocker.AsyncMock()
    videostream_channel.connect_to_server.return_value = (reader, writer)
    with pytest.raises(CallableExhausted):
        await videostream_channel.stream_video()
    expected_msg = 'test_frame'.encode()
    writer.write.assert_called_with(expected_msg)
