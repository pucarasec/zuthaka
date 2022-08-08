import asyncio
import shlex
from copy import copy
import datetime
import base64


from asgiref.sync import sync_to_async

from . import models
from .serializers import AgentSerializer
from .serializers import PostExploitationTypeSerializer
from .services.async_service import Service  # this might be a singleto
from .services.exceptions import (
    ResourceNotFoundError,
    ResourceExistsError,
    InconsistencyError,
)

from .dtos import DownloadFileDto, UploadFileDto

import logging
import csv
import re
import os

logger = logging.getLogger(__name__)


async def parser_bash_list_processes(result):
    parsed_result = []
    for element in result[1:]:
        element_info = element.split()
        parsed_result.append(
            {
                "name": element_info[-1],
                "permission": element_info[0],
                "pid": element_info[1],
                "additional_info": element,
            }
        )
    return parsed_result


async def parser_tasklist_list_process(result):
    # tasklist /v /FO:CSV
    parsed_result = []
    reader = csv.DictReader(result)
    for row in reader:
        current_dict = {
            "name": row["Image Name"],
            "pid": row["PID"],
            "permission": row["User Name"],
            "additional_info": " ".join(row.values()),
        }
        parsed_result.append(current_dict)
    return parsed_result


async def parser_powershell_list_processes(result):
    # "powershell": ("Get-Process -IncludeUserName | Sort-Object Id | Select-Object UserName, Id, CPU,HasExited, StartTime, ProcessName | ConvertTo-CSV -NoTypeInformation ",
    parsed_result = []
    reader = csv.DictReader(result)
    for row in reader:
        current_dict = {
            "name": row["ProcessName"],
            "pid": row["Id"],
            # "permission": row["UserName"],
            "permission": "",
            "additional_info": " ".join(row.values()),
        }
        parsed_result.append(current_dict)
    return parsed_result


async def parser_cmd_list_directory(self, command_result):
    # "dir /-c/q/a/o/t:w/n {}" command parsed
    parsed_result = {"files": [], "directories": []}
    datetime_format = (
        # "%m/%d/%Y  %I:%M %p %z"  # Antes de parsear , hay que agregar la tz
        # "%m/%d/%Y  %I:%H %z"  # Antes de parsear , hay que agregar la tz
        "%d/%m/%Y  %I:%H %z"  # Antes de parsear , hay que agregar la tz
    )
    tz = await self.obtain_cmd_time_zone()
    line_re = r"(.{10,10})[ ]{2}(.{8,8})[ ]+([<].+[>]|\d+)[ ]+([^\\]+)([^ ]+)[ ]+(.+)"
    for line in command_result[5:-3]:  # Saco las lineas que no me interesan
        logger.debug("line to parse: %r", line)
        splitted_line = re.search(line_re, line)
        date_time_plus_timezone = (
            splitted_line.groups()[0]
            + " "
            + splitted_line.groups()[1]
            + " "
            + tz.group()
        )
        logger.debug("date_time_plus_timezone, %r", date_time_plus_timezone)
        current_dict = {
            "additional_info": line,
            "name": splitted_line.groups()[5],
            "date": (
                datetime.datetime.strptime(
                    # date_time_plus_timezone, "%m/%d/%Y  %I:%M %p %z"
                    # date_time_plus_timezone, "%m/%d/%Y  %H:%M %z"
                    date_time_plus_timezone,
                    "%d/%m/%Y  %H:%M %z",
                )
            ).isoformat(),
        }
        if "<" not in splitted_line.groups()[2]:  # Es un archivo con tamaño en bytes
            current_dict["size"] = splitted_line.groups()[2]
            parsed_result["file"].append(current_dict)
        else:
            parsed_result["directories"].append(current_dict)
    return parsed_result


async def parser_powershell_list_directory(result):
    # gci -Force {} | Select Mode,Length, @{{Name=\"LastWriteTimeUtc\"; Expression={{$_.LastWriteTimeUTC.ToString(\"yyyy-MM-dd HH:mm:ss\")}}}},Name | ConvertTO-CSV -NoTypeInformation
    parsed_result = {"files": [], "directories": []}
    reader = csv.DictReader(result)
    # datetime_format = "%m/%d/%Y  %I:%M:%S %p %z"
    # Antes de parsear , hay que agregar la tz
    for row in reader:
        # date_time_plus_timezone = row["LastWriteTimeUtc"] + " +00:00"
        # date_time_plus_timezone = datetime.datetime.strptime(
        #     date_time_plus_timezone, datetime_format
        # ).isoformat()
        logger.debug("row: %r", row)
        try:
            current_row_dict = {
                "name": row["Name"],
                "date": row["LastWriteTimeUtc"],
                "additional_info": (" ".join(row.values())),
            }
            if row["Length"] != "":  # Es un archivo y tiene bytes
                current_row_dict["size"] = int(row["Length"])
                parsed_result["files"].append(current_row_dict)
            else:
                parsed_result["directories"].append(current_row_dict)
        except KeyError as err:
            logger.exception("invalid row: %r", row)

    return parsed_result


async def parser_bash_list_directory(result):
    # " ls -AlL --time-style=long-iso {}" command parsed
    parsed_result = {"files": [], "directories": []}
    for element in result[1:]:
        element_info = element.split()
        _date = " ".join((element_info[5], element_info[6]))
        date = datetime.datetime.strptime(_date, "%Y-%m-%d %H:%M")
        if element_info[0].startswith("d"):
            parsed_result["directories"].append(
                {
                    "name": element_info[-1],
                    "date": date.isoformat(),
                    "additional_info": element,
                }
            )
        else:
            parsed_result["files"].append(
                {
                    "name": element_info[-1],
                    "size": element_info[4],
                    "date": date.isoformat(),
                    "additional_info": element,
                }
            )
    return parsed_result


async def parse_directory(directory, shell_type):
    # HOME_LISTING_DIRECTORY = {"bash":"/home/", "cmd":"$HOMEPATH/","powershell":"$HOMEPATH/"}

    HOME_LISTING_DIRECTORY = {
        "bash": "/home/",
        "cmd": "C:/Users/",
        "powershell": "C:/Users/",
    }
    new_directory = directory.replace(
        "$ZUTHAKAHOME$", HOME_LISTING_DIRECTORY[shell_type]
    )
    return new_directory


@sync_to_async
def dto_encodedfile_to_bytes(dto):
    content = base64.b64decode(dto["content"])
    return content


@sync_to_async
def field_file_to_dto(field_file):
    name = field_file.name
    b64_content = ""
    with field_file.open(mode="rb") as f:
        content = f.read()
        b64_content = base64.b64encode(content)
    # dto.update({'file_name':name, 'file_content': b64_content.decode('utf-8')})
    return name, b64_content.decode("utf-8")

@sync_to_async
def collect_post_exploitation(agent_model):
    available_post_exploitation = models.PostExploitationType.objects.filter(c2_type=agent_model.c2.c2_type)
    serializer_class = PostExploitationTypeSerializer(available_post_exploitation, many=True)
    return serializer_class.data

@sync_to_async
def obtain_post_exploit(id_module):
    recovered_post_exploit = models.PostExploitationType.objects.get(id=id_module)
    return recovered_post_exploit

class AgentWs:
    """
    A simple implementation of the agent, that runs on the local server
    DO NO USE IN PRODUCTION is only for backend api definition porpuses
    """

    def __init__(self, agent_model):
        self.agent_model = agent_model
        self.agent_dto = AgentSerializer.to_dto_from_instance(agent_model)
        logger.info("agent-dto: %r", self.agent_dto)

    async def execute(self, cmd):
        dto = copy(self.agent_dto)
        shell_dto = dto.shell_execute
        # shell_dto.command = cmd
        logger.info("command to execute: %r", cmd)
        service = Service.get_service()
        response = await service.shell_execute(cmd, dto)
        return response

    async def shell_execute(self, command):
        logger.debug("command in shell:%r", command)
        try:
            response = await self.execute(command)
        except ConnectionError as err:
            logger.error("Connection error: %r", err, exc_info=True)
            response = {"type": "shell.result", "error": "Agent not reachable"}
        except ValueError as err:
            logger.error("Connection error: %r", err, exc_info=True)
            response = {"type": "shell.result", "error": "Agent not reachable"}
        logger.debug("response:%r", response)
        return response

    async def upload_file(self, transition_file, target_directory):
        # {'type': 'file_manager.upload', 'target_directory':'C:\\some_path', "reference":"77777-aaaaaaaa-1111-33333333"}
        dto = copy(self.agent_dto)
        target_directory = await parse_directory(
            target_directory, self.agent_model.agent_shell_type
        )
        file_name, file_content = await field_file_to_dto(transition_file)
        upload_dto = UploadFileDto(
            target_directory=target_directory,
            file_name=file_name,
            file_content=file_content,
        )
        # logger.info("dto to execute: %r", dto)
        service = Service.get_service()
        response = await service.upload_agents_file(upload_dto, dto)
        return response

    async def download_file(self, file_path):
        # {'type': 'file_manager.download', 'file_path':'C:\\Users'}
        dto = copy(self.agent_dto)
        new_file_path = await parse_directory(
            file_path, self.agent_model.agent_shell_type
        )
        download_dto = DownloadFileDto(target_file=new_file_path)
        logger.info("file to download: %r", new_file_path)
        service = Service.get_service()
        response = await service.download_agents_file(download_dto, dto)
        result = await dto_encodedfile_to_bytes(response)
        return result

    async def list_processes(self):
        shell_processes_listing = {
            "bash": ("ps aux", parser_bash_list_processes),
            "cmd": ("tasklist /v /FO:CSV", parser_tasklist_list_process),
            "powershell": ("tasklist /v /FO:CSV", parser_tasklist_list_process),
            # "powershell": ("Get-Process | Sort-Object Id | Select-Object Id, CPU,HasExited, StartTime, ProcessName | ConvertTo-CSV -NoTypeInformation ", parser_powershell_list_processes)
        }
        command, parser = shell_processes_listing[self.agent_model.agent_shell_type]
        logger.debug("command:%r", command)
        response = await self.execute(command)
        logger.debug("response:%r", response)
        content = response.get("content")
        if content:
            result = content.splitlines()
            logger.debug("result:%r", result)
            response["content"] = await parser(result)
        return response

    async def list_directory(self, directory):
        shell_listing_dictionary = {
            "bash": ("ls -AlL --time-style=long-iso {}", parser_bash_list_directory),
            "cmd": ("dir /-c/q/a/o/t:w/n {}", parser_cmd_list_directory),
            # "powershell": ("gci -Force  {} | Select-Object Mode,LastWriteTimeUtc, Length, Name | ConvertTO-CSV -NoTypeInformation ", parser_powershell_list_directory)
            "powershell": (
                'gci -Force {} | Select Mode,Length, @{{Name="LastWriteTimeUtc"; Expression={{$_.LastWriteTimeUTC.ToString("yyyy-MM-dd HH:mm:ss")}}}},Name | ConvertTO-CSV -NoTypeInformation ',
                parser_powershell_list_directory,
            ),
        }
        new_directory = await parse_directory(
            directory, self.agent_model.agent_shell_type
        )
        command = shell_listing_dictionary["powershell"][0].format(new_directory)
        parser = shell_listing_dictionary["powershell"][1]
        # logger.debug("command:%r", command)
        response = await self.execute(command)
        content = response.get("content")
        if content:
            result = content.splitlines()
            # logger.debug("result:%r", result)

            response["content"] = await parser(result)
        logger.debug("response:%r", response)
        return response

    async def obtain_cmd_time_zone(self):
        # systeminfo | findstr  /C:”Time Zone”
        # tz = re.search(r"(-+)+(.){5,5}", tz[0])  # Me devuelve el +- numero
        command = 'systeminfo | findstr  /C:"Time Zone"'
        logger.debug("command:%r", command)
        response = await self.execute(command)
        logger.debug("response:%r", response)
        content = response.get("content").splitlines()
        tz = re.search(r"(-+)+(.){5,5}", content[0])  # Me devuelve el +- numero
        logger.debug("tz: %r", tz)
        return tz

    async def process_terminate(self, pid):
        isinstance(pid, int)  # to do safety check
        shell_processes_listing = {
            "bash": "kill {}",
            "cmd": "taskkill /F /PID {}",
            "powershell": " Stop-Process -ID {} -Force ",
        }
        command = shell_processes_listing["cmd"].format(pid)
        logger.debug("command:%r", command)
        # Local handling is  exceptued
        return {"content": "process terminated"}

    async def process_inject(self, pid):
        # this might be a flag on an  implementation of post  modules
        isinstance(pid, int)  # to do safety check
        shell_processes_listing = {"bash": "kill {}", "powershell": "..."}
        command = shell_processes_listing["cmd"].format(pid)
        logger.debug("command:%r", command)
        return {"content": "Functionality not implemented"}

    async def post_exploitation_available(self):
        available_list = await collect_post_exploitation(self.agent_model)
        logger.debug("available post_exploit:%r", available_list)
        return {"content": available_list}

    async def post_exploitation_execute(self, id_module, options):
        request_dto = copy(self.agent_dto)
        # result = await post_exploit.generic_execute(options)
        post_exploit = await obtain_post_exploit(id_module)
        post_exploit_dto = PostExploitationTypeSerializer.\
            to_dto_from_instance(post_exploit, options)
        # logger.debug('[*] post_exploit_dto: {}'.post_exploit_dto)
        # logger.debug('[*] request_dt: {}'.post_exploit_dto)
        # request_dto.post_exploit = post_exploit_dto
        service = Service.get_service()
        result = await service.post_exploitation_execute(post_exploit_dto, request_dto)
        return result

        # isinstance(pid, int) # to do safety check
#         content_1 = "Started PortScan"
#         result = "ComputerName   Port  IsOpen \
# ------------   ----  ------ \
# 192.168.0.245  3000  True"
#         modules = {
#             1: (("target", "ports"), {"content": content_1}),
#             2: ((), {"content_url": "http://127.0.0.1/download?task={}"}),
#         }
#         content_2 = "Started PortScan"
#         if id_module not in modules:
#             return {
#                 "type": "post_exploitation.execute.result.error",
#                 "content": "id_module not valid",
#             }
#         for required_option in modules[id_module][0]:
#             if required_option not in options:
#                 return {
#                     "type": "post_exploitation.execute.result.error",
#                     "content": "missing required option: {}".format(required_option),
#                 }
#         return modules[id_module][1]
