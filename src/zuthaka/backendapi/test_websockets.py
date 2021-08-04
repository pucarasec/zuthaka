from django.core.management import call_command
import logging
import pytest
from django.test import TestCase
from channels.testing import WebsocketCommunicator
from channels.testing import ApplicationCommunicator
from .consumers import AgentConsumer

from django.contrib.auth.models import User
logger = logging.getLogger(__name__)


class AuthWebsocketCommunicator(WebsocketCommunicator):
    """
        Class created for  scope specification on websocket creation
    """

    def __init__(self, application, path, headers=None, subprotocols=None, scope=None):
        super(AuthWebsocketCommunicator, self).__init__(
            application, path, headers, subprotocols)
        if scope:
            self.scope.update(scope)


@pytest.fixture
def scope():
    user = User.objects.create()
    return {'type': 'websocket',
            # 'path': '/agents/1/interact/',
            # 'raw_path': b'/agents/1/interact/',
            'headers': [(b'host', b'127.0.0.1:8000'),
                        (b'connection', b'Upgrade'),
                        (b'pragma', b'no-cache'),
                        (b'cache-control', b'no-cache'),
                        (b'upgrade', b'websocket'),
                        (b'origin', b'file://'),
                        (b'sec-websocket-version', b'13'),
                        (b'user-agent',
                         b'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36'),
                        (b'accept-encoding', b'gzip, deflate, br'),
                        (b'accept-language', b'en-US,en;q=0.9'),
                        (b'sec-gpc', b'1'),
                        (b'sec-websocket-key', b'3Ba+U9C031GeRqtxfjYlbA=='),
                        (b'sec-websocket-extensions',
                         b'permessage-deflate; client_max_window_bits')],
            'query_string': b'access_token=c51b3b83ec328c77bdf0c571ebf6aff6367e4796',
            'client': ['127.0.0.1', 49996],
            'server': ['127.0.0.1', 8000],
            'subprotocols': [],
            'asgi': {'version': '3.0'},
            'user': user,
            'cookies': {},
            'path_remaining': '',
            'url_route': {'args': (), 'kwargs': {'agent_id': 1}}}


@pytest.fixture()
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'data.json')


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_task_creation(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    response = await communicator.receive_json_from(timeout=1)
    logger.info(response)
    assert response["type"] == "task.created"


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_task_reference_is_UUID(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    response = await communicator.receive_json_from(timeout=1)
    logger.info(response)
    from uuid import UUID
    try:
        assert UUID(response["reference"])
    except ValueError:
        logger.error('invalid UUID received from task reference')
        assert False


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_invalid_json(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_to("{'type': 'create.task'")
    response = await communicator.receive_json_from(timeout=1)
    logger.info(response)
    assert response['type'].lower() == 'error'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_shell_execution(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    logger.info(task)
    reference = task['reference']
    shell_execution = {"type": "shell.execute",
                       "command": "ls", "reference": reference}
    await communicator.send_json_to(shell_execution)
    result = await communicator.receive_json_from(timeout=1)
    # assert result['code'] == 200
    assert result['content'] != ''
    assert result['type'] == 'shell.execute.result'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_invalid_reference(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    logger.info(task)
    reference = task['reference']
    shell_execution = {"type": "shell.execute",
                       "command": "ls", "reference": ''}
    await communicator.send_json_to(shell_execution)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'error'


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_file_manager_list_directory(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    logger.info(task)
    reference = task['reference']
    shell_execution = {"type": "file_manager.list_directory",
                       "reference": reference,  "directory": "/"}
    await communicator.send_json_to(shell_execution)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'file_manager.list_directory.result'
    assert 'files' in result['content']
    assert 'directories' in result['content']
    assert isinstance(result['content'], dict)
    assert 'directories' in result['content']
    assert 'files' in result['content']
    assert isinstance(result['content']['directories'], list)
    assert 'additional_info' in result['content']['directories'][0]
    assert 'name' in result['content']['directories'][0]
    assert 'date' in result['content']['directories'][0]
    assert isinstance(result['content']['files'], list)
    assert 'additional_info' in result['content']['files'][0]
    assert 'name' in result['content']['files'][0]
    assert 'size' in result['content']['files'][0]
    assert 'date' in result['content']['files'][0]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_process_manager_list(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    reference = task['reference']
    process_manager_list = {
        'type': 'process_manager.list', 'reference': reference}
    await communicator.send_json_to(process_manager_list)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'process_manager.list.result'
    assert 'content' in result
    assert isinstance(result['content'], list)
    assert 'name' in result['content'][0]
    assert 'pid' in result['content'][0]
    assert 'permission' in result['content'][0]
    assert 'additional_info' in result['content'][0]


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_process_manager_terminate(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    reference = task['reference']
    process_manager_terminate = {'type': 'process_manager.terminate', 'pid':263501 ,'reference': reference}
    await communicator.send_json_to(process_manager_terminate)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'process_manager.terminate.result'
    assert 'content' in result
    assert isinstance(result['content'], str)

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_process_inject(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    reference = task['reference']
    process_manager_inject = {'type': 'process_manager.inject', 'pid':263501 ,'reference': reference}
    await communicator.send_json_to(process_manager_inject)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'process_manager.inject.result'
    assert 'content' in result
    assert isinstance(result['content'], str)

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_post_exploitation_available(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    reference = task['reference']
    post_exploitation_available = {'type': 'post_exploitation.available', 'reference': reference}
    await communicator.send_json_to(post_exploitation_available)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'post_exploitation.available.result'
    assert 'content' in result
    assert isinstance(result['content'], list)
    assert isinstance(result['content'][0], dict)
    assert 'name' in result['content'][0]
    assert 'description' in result['content'][0]
    assert 'id_module' in result['content'][0]
    assert 'options_description' in result['content'][0]
    assert isinstance(result['content'][0]['options_description'], list)
    assert 'name' in result['content'][0]['options_description'][0]
    assert 'type' in result['content'][0]['options_description'][0]
    assert 'default_value' in result['content'][0]['options_description'][0]
    assert 'description' in result['content'][0]['options_description'][0]
    assert 'example' in result['content'][0]['options_description'][0]
    assert 'required' in result['content'][0]['options_description'][0]
    assert isinstance(result['content'][0]['options_description'][0]['required'], bool)

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_post_exploitation_execute(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    reference = task['reference']
    post_exploitation_available = {'type': 'post_exploitation.execute', 'options':{'target':'192.168.0.1','ports':'80,8080,443'}, 'id_module':1, 'reference': reference}
    await communicator.send_json_to(post_exploitation_available)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'post_exploitation.execute.result.ok'
    assert 'content' in result
    assert isinstance(result['content'], str)

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_post_exploitation_execute_wrong_id(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    reference = task['reference']
    post_exploitation_available = {'type': 'post_exploitation.execute', 'options':{'target':'192.168.0.1','ports':'80,8080,443'}, 'id_module':65335, 'reference': reference}
    await communicator.send_json_to(post_exploitation_available)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'post_exploitation.execute.result.error'
    assert 'content' in result
    assert isinstance(result['content'], str)

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_post_exploitation_execute_missing_options(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    reference = task['reference']
    post_exploitation_available = {'type': 'post_exploitation.execute', 'options':{'target':'192.168.0.1'}, 'id_module':1, 'reference': reference}
    await communicator.send_json_to(post_exploitation_available)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'post_exploitation.execute.result.error'
    assert 'content' in result
    assert isinstance(result['content'], str)
    assert 'ports' in result['content']

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_post_exploitation_execute_without_options_content_url(scope, django_db_setup):
    communicator = AuthWebsocketCommunicator(
        AgentConsumer.as_asgi(), "/agents/1/interact", scope=scope)
    connected, subprotocol = await communicator.connect()
    assert connected
    await communicator.send_json_to({'type': 'create.task'})
    task = await communicator.receive_json_from(timeout=1)
    reference = task['reference']
    post_exploitation_available = {'type': 'post_exploitation.execute',  'id_module':2, 'reference': reference}
    await communicator.send_json_to(post_exploitation_available)
    result = await communicator.receive_json_from(timeout=1)
    assert result['type'] == 'post_exploitation.execute.result.ok'
    assert 'content_url' in result
    assert isinstance(result['content_url'], str)
