from .. import ResourceExistsError, ResourceNotFoundError
# from . import InconsistencyError
from .. import C2, ListenerType, LauncherType, AgentType, Options, OptionDesc, PostExploitationType

import asyncio
import random
import string
from typing import Iterable, Optional, Type, Dict, Any, IO
import json
import logging
logger = logging.getLogger(__name__)

import aiohttp
import requests
import io


class CovenantC2(C2):
    name = 'covenant_integration'
    description = 'Integration demo for presentation'
    documentation = 'https://github.com/cobbr/Covenant/wiki/'
    registered_options = [
        OptionDesc(
            name='url',
            description='Url of the corresponding API',
            example='https://127.0.0.1:7443',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='username',
            description='user owner of the API',
            example='covenantadmin',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='password',
            description='Url of the corresponding API',
            example='p4ssw0rd',
            field_type='protected-string',
            required=True
        ),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._token: Optional[str] = None
        self._listener_types = {
            CovenantHTTPListenerType.name: CovenantHTTPListenerType(
                self.options['url'],
                self
            ),
        }
        self._launcher_types = {
            CovenantPowershellLauncherType.name: CovenantPowershellLauncherType(self.options['url'], self),
        }

        self._agent_types = {
            'powershell': PowershellAgentType(self.options['url'], self),
        }

    def get_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))

    async def _get_token(self) -> str:
        """
        Authenticate the service to the corresponding Covenant
        Should we add an time expire or check to avoid generating it everytime?
        """
        data = {
            'userName': self.options['username'],
            'password': self.options['password']
        }
        target = self.options['url'] + '/api/users/login'
        async with self.get_session() as session:
            async with session.post(target, json=data) as response:
                result = await response.json()
                if result['success']:
                    self._token = result['covenantToken']
                else:
                    raise ConnectionRefusedError(
                        'Error Authenticating: {}'.format(result))
        return self._token

    async def is_alive(self) -> bool:
        try:
            await self._get_token()
        except aiohttp.InvalidURL as er:

            raise ValueError(repr(er))
        except aiohttp.ClientError as er:
            if hasattr(er, 'code') and er.code == 400:
                raise ConnectionRefusedError(repr(er))
            raise ConnectionError(repr(er))

    async def get_listener_types(self) -> Iterable[ListenerType]:
        return self._listener_types

    async def get_launcher_types(self) -> Iterable[LauncherType]:
        return self._launcher_types

    async def get_agent_types(self) -> Iterable[LauncherType]:
        return self._agent_types

    async def retrieve_agents(self, dto: Dict[str, Any]) -> bytes:
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._get_token())}
            target = '{}/api/grunts'.format(self.options['url'])

            response_dto = {'agents': []}
            async with self.get_session() as session:
                async with session.get(target, headers=headers) as response:
                    current_agents = await response.json()
                    logger.debug('current_agents: %r', len(current_agents))
                    for agent in current_agents:
                        new_agent = {}
                        new_agent['first_connection'] = agent['activationTime']
                        new_agent['last_connection'] = agent['lastCheckIn']
                        new_agent['hostname'] = agent['hostname']
                        new_agent['username'] = agent['userName']
                        new_agent['internal_id'] = agent['id']
                        new_agent['shell_type'] = 'powershell'
                        new_agent['active'] = True
                        new_agent['listener_internal_id'] = agent['listenerId']
                        response_dto['agents'].append(new_agent)
                    return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

class CovenantHTTPListenerType(ListenerType):
    name = 'default-http-profile'
    description = 'standard http listener, messages are delivered in enconded comment'
    registered_options = [
        OptionDesc(
            name='connectAddresses',
            description='address to which the agent is going to try to connect',
            example='192.168.0.14',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='connectPort',
            description='port to which the agent is going to try to connect',
            example=80,
            field_type='integer',
            required=True
        ),
        OptionDesc(
            name='bindAdress',
            description='interfaces to which the listener is bind',
            example='0.0.0.0',
            field_type='string',
            required=False
        ),
    ]

    def __init__(self, url: str, _c2: CovenantC2) -> None:
        self._url = url
        self._c2 = _c2

    async def create_listener(self, options: Options) -> Dict:
        logger.debug('[*] options:', options)
        connect_address = options.get('connectAddresses', '')
        connect_port = options.get('connectPort', '')
        if not connect_address or not connect_port:
            raise ValueError('[*] Invalid options: missing  connectAddress or connectPort')
        listener_name = 'Zuthaka-' + \
            ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for _ in range(10))

        covenant_dict = {
            "useSSL": "false",
            "urls": [connect_address],
            "name": listener_name,
            "guid": "guid",
            "description": "description-string",
            "bindAdress": "0.0.0.0",
            "bindPort": connect_port,
            "connectAddresses": [connect_address],
            "connectPort": connect_port,
            "profileId": "2",
            "listenerTypeId": "1",
            "status": "Active",
        }
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/listeners/http'.format(self._url)

            async with self._c2.get_session() as session:
                async with session.post(target, headers=headers, json=covenant_dict) as response:
                    text = await response.text()
                    if response.ok:
                        options = await response.json()
                        internal_id = options.pop('id')
                        response_dto = {}
                        response_dto['listener_internal_id'] = internal_id
                        response_dto['listener_options'] = await response.json()
                        return response_dto
                    else:
                        raise ResourceExistsError('Error creating listener: {}'.format(text))
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

    async def delete_listener(self, internal_id: str, options: Options) -> None:
        headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
        target = '{}/api/listeners/{}'.format(self._url, internal_id)
        async with self.get_session() as session:
            async with session.delete(target, headers=headers) as response:
                result = await response.text
                logger.error('[*] result: %r ', result)
                if response.ok:
                    return
                else:
                    raise ResourceNotFoundError(
                        'Error fetching listeners: {}'.format(result))

class CovenantPowershellLauncherType(LauncherType):
    name = 'Powershell Launcher'
    description = 'Uses powershell.exe to launch Agent using [systemm.reflection.assemly::load()'
    registered_options = [
        OptionDesc(
            name='Delay',
            description='Amount of time that Agent will take the agent to contact the listener in seconds',
            example='5',
            field_type='integer',
            required=True
        ),
    ]

    def __init__(self, url: str,  _c2: CovenantC2) -> None:
        self._url = url
        self._c2 = _c2

    async def create_launcher(self, dto: Dict[str, Any]) -> str:
        options = dto.get('launcher_options')
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/launchers/powershell'.format(self._url)
            listener_id = dto.get('listener_internal_id')

            creation_dict = {
                "listenerId": listener_id,
                "ImplantTemplateId": 1,
                "delay": options.get('Delay', 1),
            }  
            async with self._c2.get_session() as session:
                async with session.put(target, headers=headers, json=creation_dict) as response:
                    text = await response.text()
                    response_dto = {}
                    response_dto['launcher_internal_id'] = ''
                    response_dto['launcher_options'] = await response.json()
                    return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

    async def download_launcher(self, dto: Dict[str, Any]) -> IO:
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/launchers/powershell'.format(self._url)
            response_dto = {}
            async with self._c2.get_session() as session:
                async with session.post(target, headers=headers) as response:
                    response_dict = await response.json()
                    # logger.debug('[*] response_dict: %r ',  response_dict.keys())
                    response_dto['payload_content'] = response_dict["encodedLauncherString"]
                    response_dto['payload_name'] = response_dict["name"]
                    logger.debug('[*] payload_name: %r ',  response_dict['name'])
                    return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

class PowershellAgentType(AgentType):
    shell_type = 'powershell'

    def __init__(self, url: str, _c2: CovenantC2) -> None:
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
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/grunts/{}/interact'.format(
                self._url, dto['agent_internal_id'])
            interact_post_data = 'PowerShell /powershellcommand:"{}"'.format(
                dto['command'])

            response_dto = {}
            command_output_id = ''
            async with self._c2.get_session() as session:
                async with session.post(target, json=interact_post_data, headers=headers) as response:
                    command_response_json = await response.json()
                    command_output_id = command_response_json.get('commandOutputId')

            task_status_target = '{}/api/commands/{}'.format(self._url, command_output_id)
            for _ in range(40):
                async with self._c2.get_session() as session:
                    async with session.get(task_status_target,  headers=headers) as response:
                        command_response_json = await response.json()
                        status = command_response_json['gruntTasking']['status']
                        if status == 'completed':
                            break
                        else:
                            await asyncio.sleep(1)
            else:
                raise ConnectionError('unable  to retrieve  task')
            command_output_base_url = '{}/api/commandoutputs/{}'.format( self._url, command_output_id)
            async with self._c2.get_session() as session:
                async with session.get(command_output_base_url,  headers=headers) as response:
                    command_response_json = await response.json()
                    command_output = command_response_json['output']
                    response_dto['content'] = command_output
            return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

    async def download_file(self, dto: Dict[str, Any]) -> bytes:
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/grunts/{}/interact'.format(
                self._url, dto['agent_internal_id'])
            interact_post_data = 'Download "{}"'.format(dto['file_path'])
            logger.debug('headers: %r, target: %r, data: %r',headers, target, interact_post_data)

            response_dto = {}
            command_output_id = ''
            async with self._c2.get_session() as session:
                async with session.post(target, json=interact_post_data, headers=headers) as response:
                    command_response_json = await response.json()
                    command_output_id = command_response_json.get('commandOutputId')

            task_status_target = '{}/api/commands/{}'.format(self._url, command_output_id)
            for _ in range(40):
                async with self._c2.get_session() as session:
                    async with session.get(task_status_target,  headers=headers) as response:
                        command_response_json = await response.json()
                        status = command_response_json['gruntTasking']['status']
                        if status == 'completed':
                            break
                        else:
                            await asyncio.sleep(1)
            else:
                raise ConnectionError('unable  to retrieve  task')
            command_output_base_url = '{}/api/commandoutputs/{}'.format( self._url, command_output_id)
            async with self._c2.get_session() as session:
                async with session.get(command_output_base_url,  headers=headers) as response:
                    command_response_json = await response.json()
                    logger.debug('command_response_json: %r', command_response_json)
                    command_output = command_response_json['output']
                    response_dto['content'] = command_output
            return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

class PortScan(PostExploitationType):
    name = 'PosrtScan_integration'
    description = 'Integration demo for presentation'
    documentation = 'https://github.com/cobbr/Covenant/wiki/'
    registered_options = [
        OptionDesc(
            name='target',
            description='ip address of target machine',
            example='127.0.0.1',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='ports',
            description='ports to check',
            example='8443,80',
            field_type='string',
            required=True
        )]

    async def post_exploitation_execute(self, dto: Dict[str, Any]) -> bytes:
        """
        executes a PostExploitation module on the agent  
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        """
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/grunts/{}/interact'.format(
                self._url, dto['agent_internal_id'])
            interact_post_data = 'PortScan :"{}"'.format( dto['target'], dto['ports'])

            response_dto = {}
            command_output_id = ''
            async with self._c2.get_session() as session:
                async with session.post(target, json=interact_post_data, headers=headers) as response:
                    command_response_json = await response.json()
                    command_output_id = command_response_json.get('commandOutputId')

            task_status_target = '{}/api/commands/{}'.format(self._url, command_output_id)
            for _ in range(40):
                async with self._c2.get_session() as session:
                    async with session.get(task_status_target,  headers=headers) as response:
                        command_response_json = await response.json()
                        status = command_response_json['gruntTasking']['status']
                        if status == 'completed':
                            break
                        else:
                            await asyncio.sleep(1)
            else:
                raise ConnectionError('unable  to retrieve  task')
            command_output_base_url = '{}/api/commandoutputs/{}'.format( self._url, command_output_id)
            async with self._c2.get_session() as session:
                async with session.get(command_output_base_url,  headers=headers) as response:
                    command_response_json = await response.json()
                    command_output = command_response_json['output']
                    response_dto['content'] = command_output
            return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)
