from .. import ResourceExistsError, ResourceNotFoundError
from .. import C2, ListenerType, LauncherType, AgentType, Options, OptionDesc
from ....dtos import AgentDto, CreateListenerDto, RequestDto, ResponseDto, ShellExecuteDto, DownloadFileDto, UploadFileDto
from ....dtos import CreateLauncherDto

import asyncio
import random
import string
from typing import Optional, Dict
import aiohttp
import logging

logger = logging.getLogger(__name__)

import hmac
from hashlib import sha512
from base64 import b64encode
# from websockets import Headers
# coding: utf-8
from asgiref.sync import async_to_sync
from asgiref.sync import sync_to_async

import  base64
from base64 import b64encode
import websockets
from websockets import Headers
import hmac
from hashlib import sha512
import ssl
from urllib.parse import urlparse
import logging



class SilentTriC2(C2):
    name = 'Silent Trinity'
    description = 'Base integration of st_client'
    documentation = 'https://github.com/byt3bl33d3r/SILENTTRINITY'
    registered_options = [
        OptionDesc(
            name='teamserver_url',
            description='Url of the corresponding API',
            example='wss://127.0.0.1:8000',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='username',
            description='user owner of the API',
            example='silenttri',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='password',
            description='Url of the corresponding teamserver',
            example='p4ssw0rd',
            field_type='protected-string',
            required=True
        ),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._token: Optional[str] = None
        self._listener_types = {
            SilentTriHTTPListenerType.name: SilentTriHTTPListenerType(
                self.options['url'],
                self
            ),
        }
        self._launcher_types = {
            SilentTriPowershellLauncherType.name: SilentTriPowershellLauncherType(self.options['url'], self),
        }

        self._agent_types = {
            'powershell': PowershellAgentType(self.options['url'], self),
        }

    def get_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))

    async def _get_token(self) -> str:
        """
        Authenticate the service to the corresponding SilentTri
        Should we add an time expire or check to avoid generating it everytime?
        """
        pass

    def generate_auth_header(self, username, password):
        client_digest = hmac.new(password.encode(), msg=b'silenttrinity', digestmod=sha512).hexdigest()
        header_value = b64encode(f"{username}:{client_digest}".encode()).decode()
        return Headers({'Authorization': header_value})

    async def is_alive(self, requestDto: RequestDto) -> ResponseDto:
        """
            tries to connect to the corresponding c2 and returns ResponseDto with successful_transaction in case fo success
            raises ConectionError in case of not be able to connect to c2 instance
            raises ConnectionRefusedError in case of not be able to authenticate
        """
        username = RequestDto.c2.options.get('username')
        password = RequestDto.c2.options.get('password')
        teamserver_url = RequestDto.c2.options.get('teamserver_url')

        head = sync_to_async(generate_auth_header)(username, password)

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        URL = urlparse(teamserver_url)
        url = f"{URL.scheme}://{URL.hostname}:{URL.port}"

        async with websockets.connect(
            url, 
            extra_headers=generate_auth_header(
                username,
                password
            ), 
            ssl=ssl_context, 
            ping_interval=None, # We disable the built-in ping/heartbeat mechanism and use our own
            ping_timeout=None
        ) as ws:

            logging.info(f'Connected to {url}')
            self.ws = ws
            return True

    async def retrieve_agents(self, dto: RequestDto) -> ResponseDto:
        """
            retrives all available Agents on the  given C2
               raises ValueError in case of invalid dto
               raises ConectionError in case of not be able to connect to c2 instance
        """
        pass


class SilentTriHTTPListenerType(ListenerType):
    name = 'http-profile'
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

    def __init__(self, url: str, _c2: SilentTriC2) -> None:
        self._url = url
        self._c2 = _c2

    async def create_listener(self, options: Options, dto: RequestDto) -> Dict:
        raise NotImplementedError

    async def delete_listener(
        self,
        internal_id: str,
        options: Options,
        dto: RequestDto
    ) -> None:
        raise NotImplementedError


class SilentTriPowershellLauncherType(LauncherType):
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

    def __init__(self, url: str,  _c2: SilentTriC2) -> None:
        self._url = url
        self._c2 = _c2
    
    async def create_and_retrieve_launcher(self, options: Options, dto: RequestDto):
        """
        creates and retrieves laucnher on the corresponding C2 
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
        """
        raise NotImplementedError

class PowershellAgentType(AgentType):
    agent_shell_type = 'powershell'

    def __init__(self, url: str, _c2: SilentTriC2) -> None:
        self._url = url
        self._c2 = _c2

    async def shell_execute(self, command: str, shell_dto: ShellExecuteDto, dto: RequestDto) -> bytes:
        """
        executes a command string on the target's machine
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError
        """
        raise NotImplementedError

    async def download_file(self, download_dto: DownloadFileDto, dto: RequestDto) -> bytes:
        """
        downloads the required file from the target's machine
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        """
        raise NotImplementedError

    async def upload_file(self, upload_dto: UploadFileDto, dto: RequestDto) -> bytes:
        """
        uploads the provided file to the target's machine
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        """
        
        raise NotImplementedError
