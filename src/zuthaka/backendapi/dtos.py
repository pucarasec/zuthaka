from typing import NamedTuple, Dict, Any


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

class GenericDto(NamedTuple):
    c2_dto : C2Dto = None
    listener_dto : ListenerDto = None
    launcher_dto : LauncherDto = None