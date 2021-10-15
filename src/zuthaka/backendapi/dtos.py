from typing import NamedTuple, Dict, Any
from datetime import  date, datetime



class C2Dto(NamedTuple):
    c2_type: str
    options: Dict[str,Any] = {}

class ListenerDto(NamedTuple):
    listener_type: str
    listener_id: str = ''
    listener_internal_id: str = ''
    options: Dict[str,Any] = {}

class LauncherDto(NamedTuple):
    launcher_type: str
    options: Dict[str,Any] = {}

class ShellExecuteDto(NamedTuple):
    agent_internal_id: str
    agent_shell_type: str
    command: str

class C2InstanceDto(NamedTuple):
    c2_type: str
    options: Dict[str,Any] = {}
    c2_id : int
    listener_ids: Dict[int,str] = {}

class RequestDto(NamedTuple):
    c2: C2Dto = None
    listener: ListenerDto = None
    launcher: LauncherDto = None
    shell_execute : ShellExecuteDto = None
    c2_instances : List[C2InstanceDto] = None
    

# response
class AgentDto(NamedTuple):
    last_connection : date 
    first_connection : date
    hostname : str = ''
    username : str = ''
    interpreter :  str 
    internal_id :  str 
    listener_internal_id :  str 
    c2_id :  str 
