from typing import NamedTuple, Dict, Any, List
from datetime import date


# Requests
class C2Dto(NamedTuple):
    c2_type: str
    options: Dict[str, Any] = {}


class ListenerDto(NamedTuple):
    listener_type: str
    listener_id: str = ''
    listener_internal_id: str = ''
    options: Dict[str, Any] = {}


class LauncherDto(NamedTuple):
    launcher_type: str
    options: Dict[str, Any] = {}


class ShellExecuteDto(NamedTuple):
    agent_internal_id: str
    agent_shell_type: str


class UploadFileDto(NamedTuple):
    file_name: str
    file_content: str
    target_directory: str


class DownloadFileDto(NamedTuple):
    target_file: str

# service
class C2InstanceDto(NamedTuple):
    c2: C2Dto
    c2_id: int
    listener_ids: Dict[int, str] = {}

class RequestDto(NamedTuple):
    c2: C2Dto = None
    listener: ListenerDto = None
    launcher: LauncherDto = None
    shell_execute: ShellExecuteDto = None
    c2_instances: List[C2InstanceDto] = None
    upload_file: UploadFileDto = None
    download_file: DownloadFileDto = None


# responses
class CreateListenerDto(NamedTuple):
    listener_internal_id: str
    listener_options: dict[str, Any]


class CreateLauncherDto(NamedTuple):
    launcher_internal_id: str
    launcher_options: dict[str, Any]


class DownloadLauncherDto(NamedTuple):
    paload_content: str  # encoded launcher
    payload_name: str


class AgentDto(NamedTuple):
    last_connection: date
    first_connection: date
    interpreter:  str
    internal_id:  str
    acvtive: bool
    listener_internal_id:  str
    hostname: str = ''
    username: str = ''
    # c2_id:  str


class ResponseDto(NamedTuple):
    agents: List[AgentDto] = None
    created_listener: CreateListenerDto = None
    created_launcher: CreateLauncherDto = None
    downloaded_launcher: DownloadLauncherDto = None
    downloaded_file: DownloadFileDto = None
