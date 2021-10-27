"""

The elements of zuthaka are the ones that were created on zuthaka. Unless some action is done to be integrated (check_consistency as an action? flag try to recover lost consistency)

CONSISTENCY VS AVAILABILITY every resource that is being created, updated or deleted should prefer consistency over availability. In the other hand every list of elements and types in the system should prefer availability, but still perform some kind of consistency work. 

Naming convention? for Types(listenerTypes, C2Types, LauncherTypes)
... to be develop with parctice

"""
from typing import Dict, Any
import asyncio
from io import FileIO
import logging
from ..utils import collect_classes
logger = logging.getLogger(__name__) 
from .exceptions import ResourceNotFoundError, ResourceExistsError, InconsistencyError
from ..dtos import C2Dto, ListenerDto, LauncherDto, RequestDto


def filter_dict(original_dict, set_of_keys):
    new_dict = {}
    for key in original_dict:
        if key in set(set_of_keys):
            new_dict[key] = original_dict[key]
    return new_dict


class Service():
    """
    
    """
    _instance = None

    def __init__(self):
        raise RuntimeError('Call get_service() instead')

    @classmethod
    def get_service(cls):
        if cls._instance is None:
            from importlib.machinery import SourceFileLoader 

            from ..models import C2Type
            available_c2s_modules = []
            for c2 in C2Type.objects.all():
                available_c2s_modules.append(SourceFileLoader(c2.module_name, c2.module_path).load_module())

            available_c2s_types = {}
            from .c2 import C2
            for module in available_c2s_modules:
                c2_handler = collect_classes(module, C2)[0]
                available_c2s_types[c2_handler.name] = c2_handler

            cls._instance = cls.__new__(cls)
            cls._instance._c2types = available_c2s_types
        return cls._instance

    async def isalive_c2(self, dto: RequestDto) -> float:
        """
        tries to connect to the corresponding c2 and returns latency in seconds

           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ConnectionRefusedError in case of not be able to authenticate
           
        example dto:

        dto = { 'c2_type' :'EmpireC2Type',
          'c2_options': {
                "url": "https://127.0.0.1:7443" ,
                "username": "cobbr",
                "password": "NewPassword!"
                }
        }

        """
        try:
            if not dto.c2.c2_type:
                raise ValueError('invalid dto missing c2_type')
            current_c2_handler = self._c2types[dto.c2.c2_type]
            current_c2 = current_c2_handler(dto.c2.options)
            try:
                is_alive = await asyncio.wait_for(
                    current_c2.is_alive(dto), timeout=5.0
                    )
                # logger.debug('is_alive: %r', is_alive)
                    
            except asyncio.TimeoutError:
                raise ConnectionError
            return is_alive
        except KeyError as e:
            raise ValueError('Handler not found: {!r}'.format(e))

    async def create_listener(self, dto: RequestDto) -> Dict[str, str]:
        """
        creates an listener on the corresponding C2 and return an listener_internal_id for the corresponding API

           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceExistsError in case of not be able to create the objectdue it already exists

        example dto:

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

        response_dto = {'listener_internal_id' :'123456'}} 
        """
        try:
            c2_dto = dto.c2
            if not c2_dto:
                raise ValueError('invalid dto missing c2_dto')
            if not c2_dto.c2_type:
                raise ValueError('invalid dto missing c2_type, test')
            current_c2_handler = self._c2types[c2_dto.c2_type]
            current_c2 = current_c2_handler(c2_dto.options)

            listener_dto = dto.listener
            if not listener_dto:
                raise ValueError('invalid dto missing c2_dto')
            if not listener_dto.listener_type:
                raise ValueError('invalid dto missing listener_type')
            listener_types = await current_c2.get_listener_types()
            listener_handler = listener_types[listener_dto.listener_type]

            _listener_options = listener_dto.options
            try:
                created_listener = await asyncio.wait_for(
                    listener_handler.create_listener(_listener_options, dto),
                    timeout=5.0
                )
                # add check demo
                return created_listener
            except asyncio.TimeoutError:
                raise ConnectionError

        except KeyError as err:
            raise ValueError('Handler not found: {!r}'.format(err))

    async def delete_listener(self, dto: RequestDto):
        """
        removes a listener from a corresponding c2 instance

           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError in case of not be able to remove the object due to unfound resource

        example dto:
        dto = {
        'c2_type' :'EmpireC2Type',
        'c2_options': { 
            "url": "https://127.0.0.1:7443" ,
            "username": "cobbr",
            "password": "NewPassword!"
            }
          'listener_internal_id' :'123456',
        }
        """
        try:
            c2_dto = dto.c2
            if not c2_dto:
                raise ValueError('invalid dto missing c2_dto')
            if not c2_dto.c2_type:
                raise ValueError('invalid dto missing c2_type')
            current_c2_handler = self._c2types[c2_dto.c2_type]
            current_c2 = current_c2_handler(c2_dto.options)

            listener_dto = dto.listener
            if not listener_dto:
                raise ValueError('invalid dto missing c2_dto')
            if not listener_dto.listener_type:
                raise ValueError('invalid dto missing listener_type')
            listener_types = await current_c2.get_listener_types()
            listener_handler = listener_types[listener_dto.listener_type]

            _listener_options = listener_dto.options
            internal_id = listener_dto.listener_internal_id

            try:
                result = await asyncio.wait_for(
                    listener_handler.delete_listener(internal_id,
                                                     _listener_options,
                                                     dto),
                    timeout=5.0
                )
                return result
            except asyncio.TimeoutError:
                raise ConnectionError
        except KeyError as err:
            raise ValueError('Handler not found: {!r}'.format(err))


    async def retrieve_agents(self, dto: Dict[str, Any]) -> FileIO:
        """
        retrives all available Agents on the  given C2
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceExistsError in case of not be able to create the objectdue it already exists

           c2_id too much responsability for class implementation
            'last_connection' : '', ?UTF? valor por defecto?
            'last_connection' : '', ?UTF? valor por defecto?

        example dto:

            dto = {'c2s_intances':[{
                'c2_type' :'EmpireC2Type',
                'c2_id' :1,
                'c2_options': {
                        "url": "https://127.0.0.1:7443",
                        "username": "cobbr",
                        "password": "NewPassword!"
                    },
                'listeners_internal_ids' : ['1','2','3'] 
                }]}

            response_dto = {'agents': [
                'last_connection' : '',
                'first_connection' : '',
                'hostname' : '',
                'username' : '',
                'interpreter' : '',
                'internal_id' : '',
                'listener_internal_id' : '',
                'c2_id' : '',
            ] }

        """
        response_dto = {'agents':[]}
        for c2 in dto['c2_instances']:
            current_c2_handler = self._c2types[c2['c2_type']]
            current_c2 = current_c2_handler(c2['c2_options'])
            listener_ids = c2.pop('listener_ids')
            logger.debug('listener_ids: %r', listener_ids)
            logger.debug('dto: %r', dto)
            c2['listener_internal_ids'] = list(listener_ids.keys())
            try:
                logger.debug('c2: ',c2)
                obtained_agents =  await asyncio.wait_for(current_c2.retrieve_agents(c2), timeout=5.0)
                logger.debug('obtained_agents: %r',obtained_agents)
                current_agents = []
                for agent in obtained_agents['agents']:
                    if str(agent['listener_internal_id']) in  listener_ids:
                        new_agent = {}
                        new_agent.update(agent)
                        new_agent.update({'c2_id' :c2['c2_id']})
                        new_agent.update({'listener_id' :listener_ids[str(agent['listener_internal_id'])]})
                        current_agents.append(new_agent)
                logger.debug('current_agents: %r',current_agents)
                response_dto['agents'] += current_agents
                logger.debug('response_dto: %r',response_dto)
            except asyncio.TimeoutError:
                raise ConnectionError
        logger.debug('response_dto: ',response_dto)
        return response_dto

    async def create_launcher_and_retrieve(self, dto: Dict[str, Any]) -> Dict[str,Any]:
        """
        creates a laucnher on the corresponding C2 and return an launcher_internal_id 
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        [*] EXAMPLES 
        dto = {
        'c2_type' :'CovenantC2Type',
        'c2_options': {
                "url": "https://127.0.0.1:7443",
                "username": "cobbr",
                "password": "NewPassword!"
            },
          'listener_type' :'http',
          'listener_id' :'12',
          'listener_internal_id' :'123456',
          'listener_options' : {
                "interface": "192.168.0.1",
                "port": "139",
                "default_delay": "10",
            }
          'launcher_type' :'powershell',
          'listener_type_id' :'1',
          'launcher_options' : {
                "default_delay": "10"
            }
        }
        """
        
        try:
            _c2_type = dto.get('c2_type')
            current_c2_handler = self._c2types[_c2_type]
            _c2_options = dto.get('c2_options')
            current_c2 = current_c2_handler(_c2_options)

            _launcher_type = dto.get('launcher_type')
            launcher_types = await current_c2.get_launcher_types()
            logger.debug('dto: ', dto)
            logger.debug('launcher_types: ', launcher_types)
            launcher_handler = launcher_types[_launcher_type]

            # _launcher_options = dto.get('listener_options')
            try:
                creation_dto = filter_dict(dto, ['listener_internal_id', 'launcher_options'])
                logger.debug('creation_dto: ', creation_dto)
                created_launcher =  await asyncio.wait_for(launcher_handler.create_launcher(creation_dto), timeout=5.0)
                logger.debug(created_launcher)

                retrieve_dto = filter_dict(dto, ['listener_internal_id', 'launcher_options'])
                retrieve_dto['launcher_internal_id'] = created_launcher.get('launcher_internal_id')
                downloaded_launcher=  await asyncio.wait_for(launcher_handler.download_launcher(retrieve_dto), timeout=5.0)

                response_dto = {}
                response_dto.update(created_launcher)
                response_dto.update(downloaded_launcher)
                return response_dto
            except asyncio.TimeoutError:
                raise ConnectionError
            except KeyError as err:
                raise ValueError('invalid_dto %r',err)

        except KeyError as err:
            raise ValueError('Handler not found: {!r}'.format(err))

    async def shell_execute(self, dto: Dict[str, Any]) -> bytes:
        """
        executes command  on the  agent's computer
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        example dto:
            {'c2_type': 'EmpireC2Type',
            'c2_options': [
                    {
                        "name": "url",
                        "value": "https://127.0.0.1:7443"
                    },
                    {
                        "name": "username",
                        "value": "cobbr"
                    },
                    {
                        "name": "password",
                        "value": "NewPassword!"
                    }
                ],
                'agent_internal_id': '123',
                'agent_shell_type': 'cmd',
                'command': 'ls /usr/bin'
            }
        """
        try:
            _c2_type = dto.get('c2_type')
            current_c2_handler = self._c2types[_c2_type]
            _c2_options = dto.get('c2_options')
            current_c2 = current_c2_handler(_c2_options)

            logger.debug('dto: %r', dto)
            # logger.debug('launcher_types: ', launcher_types)
            # _launcher_options = dto.get('listener_options')
            _agent_type = dto.get('agent_shell_type', 'cmd')
            agent_types = await current_c2.get_agent_types()
            logger.debug('agent_types: %r', agent_types)
            agent_handler = agent_types[_agent_type]
            try:
                shell_result =  await asyncio.wait_for(agent_handler.shell_execute(dto), timeout=20.0)
                logger.debug(shell_result)
                response_dto = {}
                response_dto.update(shell_result)
                return response_dto
            except asyncio.TimeoutError:
                raise ConnectionError
            except KeyError as err:
                raise ValueError('invalid_dto %r',err)

        except KeyError as err:
            raise ValueError('Handler not found: {!r}'.format(err))

    async def download_agents_file(self, dto: Dict[str, Any]) -> Dict[str,Any]:
        """
        executes command  on the  agent's computer
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        example dto:
            {'c2_type': 'EmpireC2Type',
            'c2_options': [
                    {
                        "name": "url",
                        "value": "https://127.0.0.1:7443"
                    },
                    {
                        "name": "username",
                        "value": "cobbr"
                    },
                    {
                        "name": "password",
                        "value": "NewPassword!"
                    }
                ],
                'agent_internal_id': '123',
                'agent_shell_type': 'cmd',
                'file_path': 'C://Users/test',
            }
        """
        try:
            _c2_type = dto.get('c2_type')
            current_c2_handler = self._c2types[_c2_type]
            _c2_options = dto.get('c2_options')
            current_c2 = current_c2_handler(_c2_options)

            logger.debug('received dto: %r', dto)

            _agent_type = dto.get('agent_shell_type', 'powershell')
            # _agent_type = 'powershell'
            agent_types = await current_c2.get_agent_types()
            logger.debug('available agent_types in c2 handler: ', agent_types)
            agent_handler = agent_types[_agent_type]
            try:
                # retrieve_dto = filter_dict(dto, ['', 'launcher_options'])
                # retrieve_dto['launcher_internal_id'] = created_launcher.get('launcher_internal_id')
                downloaded_file =  await asyncio.wait_for(agent_handler.download_file(dto), timeout=10.0)
                logger.debug('service response dto: %r', downloaded_file)
                response_dto = {}
                response_dto.update(downloaded_file)
                return response_dto
            except asyncio.TimeoutError:
                raise ConnectionError
            except KeyError as err:
                raise ValueError('invalid_dto %r',err)
        except KeyError as err:
            raise ValueError('Handler not found: {!r}'.format(err))

    async def upload_agents_file(self, dto: Dict[str, Any]) -> Dict[str,Any]:
        """
        retrieve  agent's computer file
           raises ValueError in case of invalid dto
           raises ConectionError in case of not be able to connect to c2 instance
           raises ResourceNotFoundError 

        [*] EXAMPLES 
        example dto:
            {'c2_type': 'EmpireC2Type',
            'c2_options': [
                    {
                        "name": "url",
                        "value": "https://127.0.0.1:7443"
                    },
                    {
                        "name": "username",
                        "value": "cobbr"
                    },
                    {
                        "name": "password",
                        "value": "NewPassword!"
                    }
                ],
                'agent_internal_id': '123',
                'agent_internal_id': '123',
                'target_directory': 'C://Users/'
                'file_name': 'somefile.txt'
                'file_content': '<base64 file>'
            }
        """
        try:
            _c2_type = dto.get('c2_type')
            current_c2_handler = self._c2types[_c2_type]
            _c2_options = dto.get('c2_options')
            current_c2 = current_c2_handler(_c2_options)

            logger.debug('received dto: %r', dto)
            # logger.debug('launcher_types: ', launcher_types)
            # _launcher_options = dto.get('listener_options')

            _agent_type = dto.get('agent_shell_type', 'powershell')
            # _agent_type = 'powershell'
            agent_types = await current_c2.get_agent_types()
            logger.debug('available agent_types in c2 handler: ', agent_types)
            agent_handler = agent_types[_agent_type]
            try:
                result_dto=  await asyncio.wait_for(agent_handler.upload_file(dto), timeout=5.0)
                response_dto = {}
                response_dto.update(result_dto or {})
                return response_dto
            except asyncio.TimeoutError:
                raise ConnectionError
            except KeyError as err:
                raise ValueError('invalid_dto %r',err)
        except KeyError as err:
            raise ValueError('Handler not found: {!r}'.format(err))

    # async def post_exploitation(self, dto: Dict[str, Any]) -> str:
    #     """
    #     retrives a created launcher using an launcher_internal_id
    #        raises ValueError in case of invalid dto
    #        raises ConectionError in case of not be able to connect to c2 instance
    #        raises ResourceNotFoundError 

    #     example dto:
    #         {'c2_type': 'EmpireC2Type',
    #         'c2_options': [
    #                 {
    #                     "name": "url",
    #                     "value": "https://127.0.0.1:7443"
    #                 },
    #                 {
    #                     "name": "username",
    #                     "value": "cobbr"
    #                 },
    #                 {
    #                     "name": "password",
    #                     "value": "NewPassword!"
    #                 }
    #             ],
    #             'agent_internal_id': '123',
    #             'module' : 'port_scan',
    #             'options': [ {'name': 'target', 'ports':'80,8443'} ]
    #             """
    #     pass

    # async def post_exploitation_downloadable(self, dto: Dict[str, Any]) -> str:
    #     """
    #     retrives a created launcher using an launcher_internal_id
    #        raises ValueError in case of invalid dto
    #        raises ConectionError in case of not be able to connect to c2 instance
    #        raises ResourceNotFoundError 

    #     example dto:
    #         {'c2_type': 'EmpireC2Type',
    #         'c2_options': [
    #                 {
    #                     "name": "url",
    #                     "value": "https://127.0.0.1:7443"
    #                 },
    #                 {
    #                     "name": "username",
    #                     "value": "cobbr"
    #                 },
    #                 {
    #                     "name": "password",
    #                     "value": "NewPassword!"
    #                 }
    #             ],
    #             'agent_internal_id': '123',
    #             'module' : [
    #             'name': 'screenshot'

    #             ]
    #     """
    #     pass

    # async def get_available_post_exploitation_modules(self, dto: Dict[str, Any]) -> Dict[str,Any]:
    #     """
    #         retrives available post exploitation modules 
    #             raises ValueError in case of invalid dto
    #             raises ConectionError in case of not be able to connect to c2 instance
    #             raises ResourceNotFoundError 
    #     """
    #     _c2_type = dto.get('c2_type')
    #     current_c2_handler = self._c2types[_c2_type]
    #     _c2_options = dto.get('c2_options')
    #     current_c2 = current_c2_handler(_c2_options)

    #     logger.debug('received dto: %r', dto)
        
    #     _agent_type = dto.get('agent_type', 'powershell')
    #     agent_types = await current_c2.get_agent_types()
    #     logger.debug('available agent_types in c2 handler: ', agent_types)
    #     agent_handler = agent_types[_agent_type]

    #     try:
    #         result_dto=  await asyncio.wait_for(agent_handler.get_available_post_exploitation_modules(), timeout=5.0)
    #         response_dto = {}
    #         response_dto.update(result_dto)
    #         return response_dto
    #     except asyncio.TimeoutError:
    #         raise ConnectionError
    #     except KeyError as err:
    #         raise ValueError('invalid_dto %r',err)
    #     except KeyError as err:
    #         raise ValueError('Handler not found: {!r}'.format(err))