import pytest
import sys
import json
from pathlib import Path
base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(base_dir))
from connection_client import ConnectionClient
from utils import CallableExhausted, ErrorAfter
from request_builder import RequestBuilder

pytest_plugins = ('pytest_asyncio', )


class DummyHandler:
    async def handle(request, loop):
        return True


@pytest.fixture
def connection_client(mocker):
    client = ConnectionClient([])
    client.loop = mocker.Mock()
    client.stream_manager = mocker.Mock()
    client.event_loop_created = mocker.Mock()
    client.connection_status = mocker.Mock()
    client.connect_to_server = mocker.AsyncMock()
    client.get_messages = mocker.AsyncMock()
    return client


@pytest.fixture
def test_request():
    builder = RequestBuilder().with_args(request_type='test_request')
    request = builder.build()
    response_to_string = request.serialize() + '\n'
    return response_to_string.encode()


def test_proper_client_startup(connection_client, mocker):
    original = connection_client.register_client
    connection_client.register_client = mocker.Mock()
    mocker.patch('connection_client.asyncio.new_event_loop')
    connection_client.run_client()
    connection_client.loop.create_task.assert_any_call(
        connection_client.register_client()
    )
    connection_client.loop.create_task.assert_any_call(
        connection_client.stream_manager.run_manager()
    )
    connection_client.event_loop_created.emit.assert_called()
    connection_client.register_client = original


@pytest.mark.asyncio
async def test_success_register_client(connection_client, mocker):
    connection_client.loop = mocker.Mock()
    original_send_record = connection_client.send_records
    connection_client.send_records = mocker.AsyncMock()
    connection_client.send_records.return_value = True
    original_get_server_events = connection_client.get_server_events
    connection_client.get_server_events = mocker.Mock()
    await connection_client.register_client()
    connection_client.send_records.assert_called()
    connection_client.loop.create_task.assert_called_with(
        connection_client.get_server_events())
    connection_client.send_records = original_send_record
    connection_client.get_server_events = original_get_server_events


@pytest.mark.asyncio
async def test_failed_register_client(connection_client, mocker):
    connection_client.loop = mocker.Mock()
    original_send_record = connection_client.send_records
    connection_client.send_records = mocker.AsyncMock()
    connection_client.send_records.side_effect = ErrorAfter(limit=1,
                                                            return_value=False)
    original_get_server_events = connection_client.get_server_events
    connection_client.get_server_events = mocker.AsyncMock()
    with pytest.raises(CallableExhausted):
        await connection_client.register_client()
    connection_client.send_records.assert_called()
    connection_client.loop.create_task.assert_not_called()
    connection_client.connection_status.emit.assert_called_with(False)
    connection_client.send_records = original_send_record
    connection_client.get_server_events = original_get_server_events


@pytest.mark.asyncio
async def test_success_records_sended(connection_client, mocker):
    response = {'status': 'success'}
    reader = mocker.AsyncMock()
    reader.read.return_value = json.dumps(response).encode()
    writer = mocker.AsyncMock()
    connection_client.connect_to_server.return_value = (reader, writer)
    result = await connection_client.send_records('test_request',
                                                  'test_records')
    assert result is True


@pytest.mark.asyncio
async def test_failure_records_sended(connection_client, mocker):
    response = {'status': 'failure'}
    reader = mocker.AsyncMock()
    reader.read.return_value = json.dumps(response).encode()
    writer = mocker.AsyncMock()
    connection_client.connect_to_server.return_value = (reader, writer)
    result = await connection_client.send_records('test_request',
                                                  'test_records')
    assert result is False


@pytest.mark.asyncio
async def test_success_get_server_events(connection_client,
                                         test_request,
                                         mocker):
    reader = mocker.AsyncMock()
    writer = mocker.AsyncMock()
    connection_client.get_messages.return_value = test_request
    connection_client.connect_to_server.side_effect = ErrorAfter(
        limit=1,
        return_value=(reader, writer))
    with pytest.raises(CallableExhausted):
        await connection_client.get_server_events()
    connection_client.connection_status.emit.assert_called_with(True)


@pytest.mark.asyncio
async def test_failed_get_server_events(connection_client):
    reader = None
    writer = None
    connection_client.connect_to_server.side_effect = ErrorAfter(
        limit=1,
        return_value=(reader, writer))
    with pytest.raises(CallableExhausted):
        await connection_client.get_server_events()
    connection_client.connection_status.emit.assert_called_with(False)


@pytest.mark.asyncio
async def test_call_handler(connection_client, test_request, mocker):
    handler = DummyHandler()
    handler.handle = mocker.AsyncMock(return_value=True)
    connection_client.add_handlers(handler)
    reader = mocker.AsyncMock()
    writer = mocker.AsyncMock()
    connection_client.get_messages.return_value = test_request
    connection_client.connect_to_server.side_effect = ErrorAfter(
        limit=1,
        return_value=(reader, writer))
    with pytest.raises(CallableExhausted):
        await connection_client.get_server_events()
    connection_client.connection_status.emit.assert_called_with(True)
    handler.handle.assert_called()
