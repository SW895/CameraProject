import pytest
from ..managers import (VideoRequestManager,
                        VideoStreamManager,
                        VideoRequest,
                        StreamChannel)


# -----------------------------------------------
# ------------ Video Stream manager -------------
# -----------------------------------------------

@pytest.mark.asyncio
async def test_get_requester_with_key_error():
    pass


@pytest.mark.asyncio
async def test_get_requester_without_error():
    pass


@pytest.mark.asyncio
async def test_get_response_with_key_error():
    pass


@pytest.mark.asyncio
async def test_get_response_without_error():
    pass


@pytest.mark.asyncio
async def test_update_camera_list():
    pass


@pytest.mark.asyncio
async def test_run_channel_with_no_consumers():
    pass


@pytest.mark.asyncio
async def test_run_channel_with_consumers():
    pass


# -----------------------------------------------
# ------------ Stream Channel -------------------
# -----------------------------------------------

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
