from typing import Iterable, Optional, List, Dict
import requests

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

from .c2 import C2, Listener, ListenerType, Launcher, LauncherType, Options, OptionDesc

class EmpireC2(C2):
    name = 'empire'
    description = 'C2 developed by BC-Security'
    documentation = 'https://github.com/BC-SECURITY/Empire/wiki/RESTful-API'
    registered_options = [
        OptionDesc(
            name='url',
            description='Url of the corresponding API',
            example='https://127.0.0.1:1337',
            required=True
        ),
        OptionDesc(
            name='username',
            description='user owner of the API',
            example='empireadmin',
            required=True
        ),
        OptionDesc(
            name='password',
            description='Url of the corresponding API',
            example='https://127.0.0.1:1337',
            required=True
        ),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._token = self._get_token()
        self._listener_types: Optional[List[ListenerType]] = None
        self._launcher_types: Optional[List[LauncherType]] = None

    def _get_token(self) -> str:
        """
        Authenticate the Service to the  correponding  empire
        """
        data = {
            'username': self.options['username'],
            'password': self.options['password']
        }
        target =  self.options['url'] + '/api/admin/login'
        response = requests.post(target , json=data, verify=False)
        return response.json()['token']
    
    def authenticate(self) -> None:
        pass

    def _wrap_listener(self, listener_options: Dict) -> Listener:
        return EmpireListener(
            listener_options['name'],
            listener_options['listener_type'],
            listener_options,
            self.options['url'],
            self._token
        )
    
    def get_listener(self, name: str) -> Listener:
        params = {'token': self._token}
        target = '{}/api/listeners/{}'.format(
            self.options['url'],
            name
        )
        response = requests.get(target, params=params, verify=False)
        if response.ok:
            return self._wrap_listener(response.json()['listeners'][0])
        else:
            raise RuntimeError('Error fetching listener: {}'.format(response.status_code))

    def get_all_listeners(self) -> Iterable[Listener]:
        params = {'token': self._token}
        target =  self.options['url'] + '/api/listeners'
        response = requests.get(target, params=params, verify=False)
        if response.ok:
            return [
                self._wrap_listener(listener_options)
                for listener_options in response.json()['listeners']
            ]
        else:
            raise RuntimeError('Error fetching listeners: {}'.format(response.status_code))

    def get_listener_types(self) -> Iterable[ListenerType]:
        if self._listener_types is None:
            params = {'token': self._token}
            target =  self.options['url'] + '/api/listeners/types'
            response = requests.get(target, params=params, verify=False)
            self._listener_types = [
                EmpireListenerType(name, self.options['url'], self._token)
                for name in response.json()['types']
            ]
        return self._listener_types
    
    def get_launcher_types(self) -> Iterable[LauncherType]:
        if self._launcher_types is None:
            params = {'token': self._token}
            target =  self.options['url'] + '/api/stagers'
            response = requests.get(target, params=params, verify=False)
            self._launcher_types = [
                EmpireLauncherType(
                    stager['Name'],
                    stager['Description'],
                    [
                        OptionDesc(
                            name=name,
                            description=option_desc['Description'],
                            required=option_desc['Required']
                        )
                        for name, option_desc in stager['options'].items()
                    ],
                    self.options['url'],
                    self._token
                )
                for stager in response.json()['stagers']
            ]
        return self._launcher_types


class EmpireListenerType(ListenerType):

    name = 'HTTP(Empire)'
    description = 'base http listener'
    documentation = 'https://github.com/BC-SECURITY/Empire/wiki/RESTful-API'
    registered_options = [
        OptionDesc(
            name='url',
            description='Url of the corresponding API',
            example='https://127.0.0.1:1337',
            required=True
        ),
        OptionDesc(
            name='username',
            description='user owner of the API',
            example='empireadmin',
            required=True
        ),
        OptionDesc(
            name='password',
            description='Url of the corresponding API',
            example='https://127.0.0.1:1337',
            required=True
        ),
    ]
    def __init__(self, url: str, token: str) -> None:
        self._url = url
        self._token = token

    # @property
    # def options(self) -> Iterable[OptionDesc]:
    #     params = {'token': self._token}
    #     target = '{}/api/listeners/options/{}'.format(
    #         self._url,
    #         self.name
    #     )
    #     response = requests.get(target, params=params, verify=False)
    #     options = response.json()['listeneroptions']
    #     return [
    #         OptionDesc(
    #             name=name,
    #             example='',
    #             description=info['Description'],
    #             field_type='',
    #             required=info['Required']
    #         )
    #         for name, info in options.items()
    #     ]
    
    def create(self, name: str, options: Options) -> Listener:
        options['Name'] = name
        params = {'token': self._token}
        target = '{}/api/listeners/{}'.format(
            self._url,
            self.name
        )
        response = requests.post(target, params=params, json=options, verify=False)
        if not response.ok:
            raise RuntimeError('Error creating listener: {}'.format(response.status_code))
        return EmpireListener(options['Name'], self, options, self._url, self._token)


class EmpireListener(Listener):
    def __init__(self, name: str, listener_type: ListenerType, options: Options, url: str, token: str) -> None:
        self._name = name
        self._url = url
        self._token = token
        self.listener_type = listener_type
        self.options = options
    
    @property
    def name(self) -> str:
        return self._name
    
    def delete(self) -> None:
        params = {'token': self._token}
        target = '{}/api/listeners/{}'.format(
            self._url,
            self._name
        )
        response = requests.delete(target, params=params, verify=False)
        if not response.ok:
            raise RuntimeError('Error deleting listener: {}'.format(response.status_code))

class EmpireLauncherType(LauncherType):
    def __init__(self, name: str, description: str, options: Iterable[OptionDesc], url: str, token: str) -> None:
        self._name = name
        self._description = description
        self._options = list(options)
        self._url = url
        self._token = token

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def options(self) -> Iterable[OptionDesc]:
        return self._options

    def create(self, listener: Listener, options: Options) -> Launcher:
        options['StagerName'] = self.name
        options['Listener'] = listener.name
        params = {'token': self._token}
        target = '{}/api/stagers'.format(
            self._url
        )
        response = requests.post(target, params=params, json=options, verify=False)

        if not response.ok:
            raise RuntimeError('Error creating listener: {}'.format(response.status_code))

        launcher = response.json()[self.name]
        output = launcher['Output']
        del launcher['Output']
        options = {
            key: value['Value']
            for key, value in launcher.items()
        }
        return EmpireLauncher(self, output, options)

class EmpireLauncher(Launcher):
    def __init__(self, launcher_type: EmpireLauncherType, output: str, options: Options) -> None:
        self._launcher_type = launcher_type
        self._output = output
        self._options = options

    @property
    def output(self) -> str:
        return self._output
    
    @property
    def options(self) -> Options:
        return self._options


c2 = EmpireC2({
    'url': 'https://172.17.0.1:1337',
    'username': 'empireadmin',
    'password': 'Password123!'
})

c2.authenticate()
listener_types = {
    listener_type.name: listener_type
    for listener_type in c2.get_listener_types()
}

print('Listener types', list(listener_types.keys()))

print('Listeners', [listener.name for listener in c2.get_all_listeners()])

listener_types['http'].create('some_name', {'Port': 8080})

listener = c2.get_listener('some_name')

launcher_types = {
    launcher_type.name: launcher_type
    for launcher_type in c2.get_launcher_types()
}

print('Launcher types', list(launcher_types.keys()))

launcher = launcher_types['multi/launcher'].create(listener, {})

print(launcher.output)

listener.delete()
