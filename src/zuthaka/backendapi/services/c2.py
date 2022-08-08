from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, List, Iterable, Any, NamedTuple

from ..dtos import DownloadFileDto, RequestDto, ShellExecuteDto, UploadFileDto
from ..dtos import ResponseDto
from asgiref.sync import sync_to_async
import logging

logger = logging.getLogger(__name__)

Options = Dict[str, str]


# utils
def sync_save_payload(name, payload):
    with open(name, "wb") as f:
        f.wirte(payload)


def async_save_payload(name, payload):
    sync_to_async(sync_save_payload)(name, payload)


class OptionDesc(NamedTuple):
    name: str = ""
    example: str = ""
    description: str = ""
    field_type: str = ""
    required: bool = True


class C2(ABC):
    name: str
    description: str
    documentation: str
    registered_options: List[OptionDesc]

    def __init__(self, options: Options) -> None:
        _is_valid = self.__class__.validate_options(options)
        if not _is_valid:
            raise ValueError("Invalid options")
        self.options = options

    @classmethod
    def validate_options(cls, options: Options) -> bool:
        for option in cls.registered_options:
            if option.name not in options:
                logger.debug("option missing: %r", option)
        return all(option.name in options for option in cls.registered_options)

    async def get_listener_types(self) -> Iterable["ListenerType"]:
        """
        Returns a dictionary with all the registered listener types
        """
        return self._listener_types

    async def get_launcher_types(self) -> Iterable["LauncherType"]:
        """
        Returns a dictionary with all the registered launcher types
        """
        return self._launcher_types

    async def get_agent_types(self) -> Iterable["LauncherType"]:
        """
        Returns a dictionary with all the registered agents types
        """
        return self._agent_types

    @abstractmethod
    async def is_alive(self, request_dto: RequestDto) -> ResponseDto:
        """
        tries to connect to the corresponding c2 and returns ResponseDto with successful_transaction in case fo success
        raises ConectionError in case of not be able to connect to c2 instance
        raises ConnectionRefusedError in case of not be able to authenticate
        """
        pass

    @abstractmethod
    async def retrieve_agents(self, dto: RequestDto) -> ResponseDto:
        """
        retrives all available Agents on the  given C2
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
        """
        pass

class ListenerType(ABC):
    """Listener Factory"""

    @abstractmethod
    async def create_listener(self, options: Options, dto: RequestDto) -> ResponseDto:
        """
        creates an listener on the corresponding C2 and return a Listener with
        listener_internal_id for the corresponding API inside ResponseDto

           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceExistsError in case of not be able to create the objectdue it already exists
        """
        pass

    @abstractmethod
    async def delete_listener(
        self, internal_id: str, options: Options, dto: RequestDto
    ) -> ResponseDto:

        """
        removes a listener from a corresponding c2 instance
        returns ResponseDto with successful_transaction in case fo success

           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError in case of not be able to remove the object due to unfound resource

        """
        pass


class LauncherType(ABC):
    """Launcher Factory"""

    @abstractmethod
    async def create_and_retrieve_launcher(
        self, options: Options, dto: RequestDto
    ) -> str:
        """
        creates and retrieves laucnher on the corresponding C2
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
        """
        raise NotImplementedError


class AgentType(ABC):
    async def shell_execute(
        self, command: str, shell_dto: ShellExecuteDto, dto: RequestDto
    ) -> bytes:
        """
        executes a command string on the target's machine
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError

        """
        pass

    async def download_file(
        self, download_dto: DownloadFileDto, dto: RequestDto
    ) -> bytes:
        """
        downloads required file from the target's machine
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError

        """
        pass

    async def upload_file(self, upload_dto: UploadFileDto, dto: RequestDto) -> bytes:
        """
        uploads required file to the target's machine
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError

        """
        raise NotImplementedError

    async def get_available_post_exploitation_modules(self) -> Iterable["PostExploitation"]:
        return self.post_exploitation_types


class PostExploitationType(ABC):
     
    @abstractmethod
    async def execute(
        self, options: Options, dto: RequestDto
    ) -> str:
        raise NotImplementedError

    # @abstractmethod
    # async def file_execute(
    #     self, options: Options, dto: RequestDto
    # ) -> str:
    #     raise NotImplementedError