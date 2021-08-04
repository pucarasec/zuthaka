from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, List, Iterable, Any, NamedTuple

from asgiref.sync import sync_to_async
import logging
logger = logging.getLogger(__name__)

Options = Dict[str, str]

# pylint: disable=inherit-non-class
class OptionDesc(NamedTuple):
    name: str= ''
    example: str= ''
    description: str= ''
    field_type: str= ''
    required: bool = True

    # def __str__(self):
    #     return f'name: {self.name}, example: {self.example}, description: {self.description}, field_type: {self.field_type}, required: {self.required}'

    # def __repr__(self):
    #     return f'name: {self.name}, example: {self.example}, description: {self.description}, field_type: {self.field_type}, required: {self.required}'

class C2(ABC):
    name: str
    description: str
    documentation: str
    registered_options: List[OptionDesc]

    def __init__(self, options: Options) -> None:
        _is_valid = self.__class__.validate_options(options)
        if not _is_valid :
            raise ValueError('Invalid options')
        self.options = options

    @abstractmethod
    async def is_alive(self, name: str) -> bool:
        """
            tries to connect to the corresponding c2 and returns bool
            raises ConectionError in case of not be able to connect to c2 instance
            raises ConnectionRefusedError in case of not be able to authenticate
        """
        pass
    
    @abstractmethod
    async def get_listener_types(self) -> Dict[str, 'ListenerType']:
        """
            Returns a dictionary with all the registered listener types 
        """
        pass

    @abstractmethod
    async def get_launcher_types(self) -> Iterable['LauncherType']:
        """
            Returns a dictionary with all the registered launcher types 
        """
        pass

    @abstractmethod
    async def retrieve_agents(self, dto: Dict[str, Any]) -> bytes:
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
        logger.debug('cls.registered_options: %r ', cls.registered_options )
        logger.debug('options: %s', options)
        for  option in cls.registered_options:
            if option.name not in options:
                logger.debug('option missing: %r', option)
        return all(option.name in options for option in cls.registered_options)

class ListenerType(ABC):
    """ Listener Factory """

    @abstractmethod
    async def create_listener(self, options: Options) -> 'Listener':
        """
        creates an listener on the corresponding C2 and return a Listener with listener_internal_id for the corresponding API

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
    async def delete_listener(self, internal_id:str, options: Options) -> None:

        """
        removes a listener from a corresponding c2 instance

           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError in case of not be able to remove the object due to unfound resource

        """
        pass

    # @abstractmethod
    # async def get_options(self) -> Iterable[OptionDesc]:
    #     pass

    # @property
    # @abstractmethod
    # def name(self) -> str:
    #     pass

# class Listener(ABC):
#     @property
#     # @abstractmethod
#     def internal_id(self) -> str:
#         pass

#     @property
#     # @abstractmethod
#     def options(self) -> str:
#         pass

#     def to_dto(self):
#         dto = {
#                 'listener_id': self.internal_id,
#                 'listener_options': self.options
#             }
#         return dto

class LauncherType(ABC):
    """ Launcher Factory """

    @abstractmethod
    async def create_launcher(self, dto: Dict[str, Any]) -> str:
        """
        creates a laucnher on the corresponding C2 and return an launcher_internal_id raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceExistsError in case of not be able to create the objectdue it already exists

        """
        raise NotImplementedError
        
    @abstractmethod
    async def download_launcher(self, dto: Dict[str, Any]) -> bytes:
        """
        retrives a created launcher using an launcher_internal_id
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 
        """
        raise NotImplementedError
        

class Launcher(ABC):
    @property
    @abstractmethod
    async def output(self) -> str:
        pass

    @abstractmethod
    async def get_options(self) -> Options:
        pass

class AgentType(ABC):

    async def retreive_agents(self, dto: Dict[str, Any]) -> bytes:
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
        """

        pass

    async def shell_execute(self, dto: Dict[str, Any]) -> bytes:
        """
        executes a command string on the 
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        """
        pass

class PostExploitationType(ABC):
    async def post_exploitation_execute(self, dto: Dict[str, Any]) -> bytes:
        pass

def sync_save_payload(name, payload):
    with open(name,'wb') as f:
            f.wirte(payload)

def async_save_payload(name, payload):
    sync_to_async(sync_save_payload)(name,payload)
