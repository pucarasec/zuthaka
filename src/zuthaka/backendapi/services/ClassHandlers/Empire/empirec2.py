from .. import ResourceExistsError, ResourceNotFoundError

# from . import InconsistencyError
# from .. import C2, ListenerType, LauncherType, AgentType, Options, OptionDesc, PostExploitationType
from .. import C2, ListenerType, LauncherType, AgentType, Options, OptionDesc

import asyncio
import random
import string
from typing import Iterable, Optional, Type, Dict, Any, IO
import logging

logger = logging.getLogger(__name__)

import aiohttp
import requests
import io


class EmpireC2(C2):
    name = "empire_integration"
    description = "Integration demo for presentation"
    documentation = "https://github.com/BC-SECURITY/empire"
    registered_options = [
        OptionDesc(
            name="url",
            description="Url of the corresponding API",
            example="https://127.0.0.1:1337",
            field_type="string",
            required=True,
        ),
        OptionDesc(
            name="username",
            description="user owner of the API",
            example="empireadmin",
            field_type="string",
            required=True,
        ),
        OptionDesc(
            name="password",
            description="Url of the corresponding API",
            example="https://127.0.0.1:1337",
            field_type="string",
            required=True,
        ),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._token: Optional[str] = None

        self._listener_types = {
            EmpireHTTPListenerType.name: EmpireHTTPListenerType(
                self.options["url"], self
            ),
        }
        self._launcher_types = {
            EmpireDllLauncherType.name: EmpireDllLauncherType(
                self.options["url"], self
            ),
        }

        self._agent_types = {
            "powershell": PowershellAgentType(self.options["url"], self),
        }

    async def get_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))

    async def _get_token(self) -> str:
        """
        Authenticate the Service to the  correponding  empire
        """
        if self._token is None:
            data = {
                "username": self.options["username"],
                "password": self.options["password"],
            }
            target = self.options["url"] + "/api/admin/login"
            async with self.get_session() as session:
                async with session.post(target, json=data) as response:
                    self._token = (await response.json())["token"]

        return self._token

    async def is_alive(self) -> bool:
        try:
            await self._get_token()
        except aiohttp.InvalidURL as er:

            raise ValueError(repr(er))
        except aiohttp.ClientError as er:
            if hasattr(er, "code") and er.code == 400:
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

            params = {"token": await self._c2.get_token()}
            target = "{}/api/listeners/http".format(self._url)

            response_dto = {"agents": []}
            async with self._c2.get_session() as session:
                async with session.get(target, params=params) as response:
                    current_agents = await response.json()
                    logger.debug("current_agents: %r", current_agents)

                    for agent in current_agents:
                        new_agent = {}
                        new_agent["hostname"] = agent["hostname"]
                        new_agent["last_connection"] = agent["lastseen_time"]
                        new_agent["username"] = agent["username"]
                        new_agent["first_connection"] = agent["checkin_time"]
                        new_agent["internal_id"] = agent["name"]
                        new_agent["shell_type"] = agent["process_name"]
                        new_agent["listener_internal_id"] = 1  # WARNING!!!
                        response_dto["agents"].append(new_agent)
                    return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)


class EmpireHTTPListenerType(ListenerType):
    name = "empire-http-profile"
    description = "standard http listener, messages are delivered in enconded comment"
    registered_options = [
        OptionDesc(
            name="port",
            description="port for the listener",
            example="8888",
            field_type="string",
            required=True,
        ),
        OptionDesc(
            name="host",
            description="Hostname/IP for staging",
            example="http://192.168.52.173:8080",
            field_type="string",
            required=True,
        ),
        OptionDesc(
            name="delay",
            description="Agent delay/reach back interval (in seconds).",
            example=1,
            field_type="integer",
            required=False,
        ),
    ]

    def __init__(self, url: str, _c2: EmpireC2) -> None:
        self._url = url
        self._c2 = _c2

    async def create_listener(self, options: Options) -> Dict:
        logger.debug("[*] options:", options)
        host = options.get("host", "")
        port = options.get("port", "")
        delay = options.get("delay", 0)

        if not port or not host:
            raise ValueError(
                "[*] Invalid options: missing  connectAddress or connectPort"
            )

        listener_name = "Zuthaka-" + "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
        )
        post_dict = {
            "Name": listener_name,
            "Port": port,
            "Host": host,
            "DefaultDelay": host,
        }
        try:
            params = {"token": await self._c2.get_token()}
            target = "{}/api/listeners/http".format(self._url)
            async with self._c2.get_session() as session:
                async with session.get(target, params=params) as response:
                    text = await response.text()
                    if response.ok:
                        options = await response.json()
                        if options["success"]:
                            response_dto = {}
                            response_dto["listener_internal_id"] = listener_name
                            return response_dto
                        else:
                            raise ResourceExistsError(
                                "Error creating listener: {}".format(text)
                            )
                    else:
                        raise ResourceExistsError(
                            "Error creating listener: {}".format(text)
                        )
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

    async def delete_listener(self, internal_id: str, options: Options) -> None:
        params = {"token": await self._c2.get_token()}
        target = "{}/api/listeners/{}".format(self._url, listener_id)
        async with self.get_session() as session:
            async with session.delete(target, params=params) as response:
                result = await response.text
                logger.error("[*] result: %r ", result)
                if response.ok:
                    return
                else:
                    raise ResourceNotFoundError(
                        "Error fetching listeners: {}".format(result)
                    )


class EmpireDllLauncherType(LauncherType):
    name = "Dll Launcher"
    description = "Generate a PowerPick Reflective DLL to inject with stager code."
    registered_options = [
        OptionDesc(
            name="arch",
            description="Architecture of the .dll to generate (x64 or x86)",
            example="x64",
            field_type="string",
            required=False,
        ),
    ]

    def __init__(self, url: str, _c2: EmpireC2) -> None:
        self._url = url
        self._c2 = _c2

    async def create_launcher(self, dto: Dict[str, Any]) -> str:
        arch = dto.get("arch", "x64")
        try:
            params = {"token": await self._c2.get_token()}
            target = "{}/api/stagers/dll".format(self._url)
            listener_id = dto.get("listener_internal_id")

            launcher_name = "Zuthaka-" + "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
            )
            creation_dict = {
                "Listener": listener_id,
                "StagerName": launcher_name,
                "Arch": arch,
            }
            async with self._c2.get_session() as session:
                async with session.post(
                    target, params=params, json=creation_dict
                ) as response:
                    text = await response.text()
                    response_dto = {}
                    response_dto["launcher_internal_id"] = ""
                    response_dto["launcher_options"] = await response.json()
                    return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)

    async def download_launcher(self, dto: Dict[str, Any]) -> IO:
        arch = dto.get("arch", "x64")
        try:
            params = {"token": await self._c2.get_token()}
            target = "{}/api/stagers/dll".format(self._url)
            listener_id = dto.get("listener_internal_id")

            launcher_name = "Zuthaka-" + "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
            )
            creation_dict = {
                "Listener": listener_id,
                "StagerName": launcher_name,
                "Arch": arch,
            }
            async with self._c2.get_session() as session:
                async with session.post(
                    target, params=params, json=creation_dict
                ) as response:
                    response_dict = await response.json()
                    logger.debug("[*] response_dict: %r ", response_dict.keys())
                    response_dto["payload_content"] = response_dict["Output"]
                    response_dto["payload_name"] = "launcher.dll"
                    return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)


class PowershellAgentType(AgentType):
    shell_type = "powershell"

    def __init__(self, url: str, _c2: EmpireC2) -> None:
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
            agent_id = dto["agent_internal_id"]
            params = {"token": await self._c2.get_token()}
            target = "{}/api/agents/{}/shell".format(self._url, agent_id)
            interact_post_data = {"command": dto["command"]}

            response_dto = {}
            command_output_id = ""
            async with self._c2.get_session() as session:
                async with session.post(
                    target, params=params, json=creation_dict
                ) as response:
                    command_response_json = await response.json()
                    command_output_id = command_response_json.get("taskID")

            task_status_target = "{}/api/agents/{}/results".format(self._url, agent_id)
            for _ in range(40):
                async with self._c2.get_session() as session:
                    async with session.get(
                        task_status_target, headers=headers
                    ) as response:
                        results_json = await response.json()
                        result = None
                        for obtained_result in results_json:
                            if obtained_result["taskID"] == command_output_id:
                                result = obtained_result
                        if result:
                            break
                        else:
                            await asyncio.sleep(1)
            else:
                raise ConnectionError("unable  to retrieve  task")

            response_dto["content"] = result["results"]
            return response_dto
        except aiohttp.client_exceptions.ClientConnectorError as err:
            raise ConnectionError(err)


#     async def download_file(self, dto: Dict[str, Any]) -> bytes:
#         try:
#             agent_id = dto['agent_internal_id']
#             params = {'token': await self._c2.get_token()}
#             target = '{}/api/agents/{}/shell'.format(self._url, agent_id)

#             interact_post_data = 'Download "{}"'.format(dto['file_path'])
#             logger.debug('headers: %r, target: %r, data: %r',headers, target, interact_post_data)

#             response_dto = {}
#             command_output_id = ''
#             async with self._c2.get_session() as session:
#                 async with session.post(target, json=interact_post_data, headers=headers) as response:
#                     command_response_json = await response.json()
#                     command_output_id = command_response_json.get('commandOutputId')

#             task_status_target = '{}/api/commands/{}'.format(self._url, command_output_id)
#             for _ in range(40):
#                 async with self._c2.get_session() as session:
#                     async with session.get(task_status_target,  headers=headers) as response:
#                         command_response_json = await response.json()
#                         status = command_response_json['gruntTasking']['status']
#                         if status == 'completed':
#                             break
#                         else:
#                             await asyncio.sleep(1)
#             else:
#                 raise ConnectionError('unable  to retrieve  task')
#             command_output_base_url = '{}/api/commandoutputs/{}'.format( self._url, command_output_id)
#             async with self._c2.get_session() as session:
#                 async with session.get(command_output_base_url,  headers=headers) as response:
#                     command_response_json = await response.json()
#                     logger.debug('command_response_json: %r', command_response_json)
#                     command_output = command_response_json['output']
#                     response_dto['content'] = command_output
#             return response_dto
#         except aiohttp.client_exceptions.ClientConnectorError as err:
#             raise ConnectionError(err)
