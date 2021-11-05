from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, List, Iterable, Any, NamedTuple

from ..dtos import DownloadFileDto, RequestDto, ShellExecuteDto, UploadFileDto
from asgiref.sync import sync_to_async
import logging
logger = logging.getLogger(__name__)

Options = Dict[str, str]


# utils
def sync_save_payload(name, payload):
    with open(name, 'wb') as f:
        f.wirte(payload)


def async_save_payload(name, payload):
    sync_to_async(sync_save_payload)(name, payload)


# pylint: disable=inherit-non-class
class OptionDesc(NamedTuple):
    name: str = ''
    example: str = ''
    description: str = ''
    field_type: str = ''
    required: bool = True

class C2(ABC):
    name: str
    description: str
    documentation: str
    registered_options: List[OptionDesc]

    def __init__(self, options: Options) -> None:
        _is_valid = self.__class__.validate_options(options)
        if not _is_valid:
            raise ValueError('Invalid options')
        self.options = options

    @abstractmethod
    async def is_alive(self, request_dto: RequestDto) -> bool:
        """
            tries to connect to the corresponding c2 and returns bool
            raises ConectionError in case of not be able to connect to c2 instance
            raises ConnectionRefusedError in case of not be able to authenticate
        """
        pass
    
    async def get_listener_types(self) -> Iterable['ListenerType']:
        """
            Returns a dictionary with all the registered listener types 
        """
        return self._listener_types

    async def get_launcher_types(self) -> Iterable['LauncherType']:
        """
            Returns a dictionary with all the registered launcher types 
        """
        return self._launcher_types

    async def get_agent_types(self) -> Iterable['LauncherType']:
        """
            Returns a dictionary with all the registered agents types 
        """
        return self._agent_types

    @abstractmethod
    # async def retrieve_agents(self, listener_internal_ids: List[int], c2_dto: C2Dto, dto: RequestDto) -> bytes:
    async def retrieve_agents(self, dto: RequestDto) -> bytes:
        """
            retrives all available Agents on the  given C2
               raises ValueError in case of invalid dto
               raises ConectionError in case of not be able to connect to c2 instance
               raises ResourceNotFoundError 

            [*] EXAMPLES 

            dto = {
                'c2_type' :'EmpireC2Type',
                'c2_options': {
                        "url": "https://127.0.0.1:7443",
                        "username": "cobbr",
                        "password": "NewPassword!"
                    },
                  'listeners_internal_ids' : ['1','2','3'] 
                  }

            response_dto = {'agents': [{
                'last_connection' : '',
                'first_connection' : '',
                'hostname' : '',
                'username' : '',
                'internal_id' : ''
                'shell_type' : ''
                'listener_internal_id' : ''
                }, ]
                }
        """
        pass
    
    @classmethod
    def validate_options(cls, options: Options) -> bool:
        # logger.debug('options: %s', options)
        for option in cls.registered_options:
            if option.name not in options:
                logger.debug('option missing: %r', option)
        return all(option.name in options for option in cls.registered_options)


class ListenerType(ABC):
    """ Listener Factory """

    @abstractmethod
    async def create_listener(
        self,
        options: Options,
        dto: RequestDto
    ) -> 'Listener':
        """
        creates an listener on the corresponding C2 and return a Listener with
        listener_internal_id for the corresponding API

           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceExistsError in case of not be able to create the objectdue it already exists

        [*] EXAMPLES 

        dto = {
            'c2_type' :'EmpireC2Type',
            'c2_options': {
                    "url": "https://127.0.0.1:7443",
                    "username": "cobbr",
                    "password": "NewPassword!"
                },
              'listener_type' :'HTTPEmpire',
              'listener_options' : {
                    "interface": "192.168.0.1",
                    "port": "139",
                    "default_delay": "10",
                }
            }
        """
        pass

    @abstractmethod
    async def delete_listener(
        self,
        internal_id: str,
        options: Options,
        dto: RequestDto
    ) -> None:

        """
        removes a listener from a corresponding c2 instance

           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError in case of not be able to remove the object due to unfound resource

        """
        pass

class LauncherType(ABC):
    """ Launcher Factory """

    @abstractmethod
    async def create_and_retrieve_launcher(self, options: Options, dto: RequestDto) -> str:
        """
        creates and retrieves laucnher on the corresponding C2 
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
        """
        raise NotImplementedError

class AgentType(ABC):

    async def shell_execute(self, command: str, shell_dto: ShellExecuteDto, dto: RequestDto) -> bytes:
        """
        executes a command string on the 
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        """
        pass


    async def download_file(self, download_dto: DownloadFileDto, shell_dto: ShellExecuteDto, dto: RequestDto) -> bytes:
        """
        downloads required file from the target's machine
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        """
        pass

    async def upload_file(self, upload_dto: UploadFileDto, shell_dto: ShellExecuteDto, dto: RequestDto) -> bytes:
        """
        uploads required file to the target's machine
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        """
        pass