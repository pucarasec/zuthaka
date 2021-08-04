from ..c2 import C2, Listener, ListenerType, Launcher, LauncherType, Options, OptionDesc

class TemplateC2Type(C2):
    # all this information is given to the user when using the interface
    name = 'template_c2'
    description = 'this is an example C2'
    documentation = 'https://super.awesome.c2/docs/'
    registered_options = [
        OptionDesc(
            name='url',
            description='Url of the corresponding API',
            example='https://127.0.0.1:31337',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='username',
            description='user owner of the API',
            example='pucara',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='password',
            description='Url of the corresponding API',
            example='p4ssw0rd',
            field_type='string',
            required=True
        ),
    ]

    async def is_alive(self) -> bool:
        """
           raises ConectionError in case of not be able to connect to c2 instance
           raises ConnectionRefusedError in case of not be able to authenticate
        """
        pass

    async def _get_token(self) -> str:
        """

        Authenticate the service to the corresponding Covenant

        Should we add an time expire or check to avoid generating it everytime?

        """
        data = {
            'userName': self.options['username'],
            'password': self.options['password']
        }
        target =  self.options['url'] + '/api/users/login'
        async with self.get_session() as session:
            async with session.post(target, json=data) as response:
                result = await response.json()
                if result['success']:
                    self._token = result['covenantToken']
                else: 
                    raise ConnectionRefusedError('Error Authenticating: {}'.format(result))
        return self._token
    
    def authenticate(self) -> None:
        pass

    async def get_listener_types(self) -> Iterable[ListenerType]:
        return self._listener_types

    async def get_listener(self, name: str) -> 'Listener':
        raise NotImplementedError()
    
    async def get_all_listeners(self) -> Iterable['Listener']:
        """
            Is this method  necesary? 
        """
        headers = {'Authorization': 'Bearer {}'.format(self._token)}
        target =  self.options['url'] + '/api/listeners'
        async with self.get_session() as session:
            async with session.get(target, headers=headers) as response:
                result = await response.json()
                # print('[*] result: ',result)
                if response.ok:
                    return [
                        self._wrap_listener(listener_d)
                        for listener_d in result
                    ]
                else:
                    raise RuntimeError('Error fetching listeners: {}'.format(response.status))

    def get_launcher_types(self) -> Iterable[LauncherType]:
        raise NotImplementedError()

    def _wrap_listener(self, listener_d: Dict) -> Listener:
        """
            Is this function needed?
        """
        _listener = CovenantHTTPListener(self._listener_types[0], listener_d)
        # _listener.options = listener_d
        return _listener

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._token: Optional[str] = None
        self._listener_types = [
            CovenantHTTPListenerType(
                self.options['url'],
                self
            ),
        ]
    
    def get_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False))

class CovenantHTTPListenerType(ListenerType):
    name = 'http'
    description = 'standard http listener, messages are delivered in enconded comment'
    registered_options = [
        OptionDesc(
            name='useSSL',
            description='ssl enabled communication between agent and listener',
            example='false',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='bindPort',
            description='port in which the listener is going to receive agent\'s connections',
            example=80,
            field_type='integer',
            required=True
        ),
        OptionDesc(
            name='connectAddresses',
            description='port in which the listener is going to receive agent\'s connections',
            example='0.0.0.0',
            field_type='string',
            required=True
        ),
        OptionDesc(
            name='connectAddresses',
            description='??',
            example=80,
            field_type='integer',
            required=True
        ),
    ]

    # def __init__(self, url: str, token: str) -> None:
    def __init__(self, url: str, _c2: CovenantC2) -> None:
        self._url = url
        self._c2 = _c2
    
    async def create(self, name: str, options: Options) -> Listener:
        port_to_use = 80
        _options = {
            "useSSL": "false",  # If Set to true you need addtional parameters   "sslCertificate": "string",
            # "sslCertificatePassword": "string",
            # "sslCertHash": "string", # Need to test , we not know what
            "bindAdress": "0.0.0.0",
            "bindPort": port_to_use,  # The bind and connect port can be different
            "connectAddresses": ['127.0.0.1'],  # Its a list, you can write multiples IP's
            "connectPort": port_to_use,  # This refers to the port in the attackers machine
            "profileId": "2",  # 1 equals Custom HTTP Profile , 2 equals DefaultHTTP Profile
            "listenerTypeId": "1",  # 1 equals HTTP Listeners , 2 equals Bridge Listeners
            "status": "Active",  # Its not neccesary but it you not send this, its start as unitialized
        }  # This represent the bare minimun that is requiered to create a listeners

        _options['Name'] = name
        headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
        # target = '{}/api/listeners/http'.format(self._c2.options['url'])
        target = '{}/api/listeners/http'.format(self._url)

        async with self._c2.get_session() as session:
            async with session.post(target, headers=headers, json=_options) as response:
                if response.ok:
                    options = await response.json()
                    return CovenantHTTPListener(self, options)
                else:
                    print('[*] headers: ',headers)
                    print('[*] target: ',target)
                    print('[*] response: ',response)
                    print('[*] response.ok: ',response.ok)
                    print('[*] options: ', options)
                    print('[*] _options: ', _options)
                    raise RuntimeError('Error creating listener: {}'.format(response.status))

    async def delete(self) -> None:
        headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
        _id = options['id']
        target = '{}/api/listeners/{}'.format(self._url, self.options['id'])
        async with self.get_session() as session:
            async with session.delete(target, headers=headers) as response:
                result = await response.json()
                # print('[*] result: ',result)
                if response.ok:
                    return [
                        self._wrap_listener(listener_d)
                        for listener_d in result
                    ]
                else:
                    raise RuntimeError('Error fetching listeners: {}'.format(response.status))
    
    # @property
    # def options(self) -> Iterable[OptionDesc]:
    #     return self._options 

    async def get_options(self) -> Iterable[OptionDesc]:
        return registered_options

    @property
    def name(self) -> str:
        return 'http'

class CovenantHTTPListener(Listener):
    def __init__(self, _listener_type: CovenantHTTPListenerType, options: Options) -> None:
        self._listener_type = _listener_type
        print(self._listener_type._c2)
        self._url = self._listener_type._url # this should be done  with a "super" call
        self._options = options
        self._name = self._options['id']
    
    @property
    def name(self) -> str:
        return self._name
    
    async def delete(self) -> None:
        headers = {'Authorization': 'Bearer {}'.format(await self._c2._get_token())}
        _id = options['id']
        target = '{}/api/listeners/{}'.format(self._url, self._options['id'])
        async with self.get_session() as session:
            async with session.delete(target, headers=headers) as response:
                result = await response.json()
                # print('[*] result: ',result)
                if response.ok:
                    return [
                        self._wrap_listener(listener_d)
                        for listener_d in result
                    ]
                else:
                    raise RuntimeError('Error fetching listeners: {}'.format(response.status))
        

###############################

#import urllib3
#urllib3.disable_warnings()

## Cosas que fui viendo de como pegarle a la API de Covenant
## Primer Paso - Obtener un Token que luego se usa para autenticar 

#base_url='https://127.0.0.1:7443'
#username='admin' # CAMBIAR
#password='aguantecortana' # CAMBIAR
#current_ip = "192.168.101.78" # CAMBIAR
#r1=requests.post(base_url+'/api/users/login',json={'userName':username,'password':password},verify=False)
## r1.text contiene la respuesta y con [33:-2] me quedo con solamente el token 
#token=r1.text[33:-2]
##if 'true' in r1.text: # Para saber si pudo autenticar o no ya que siempre deveulve 200 
#header={"Authorization":"Bearer {} ".format(token)}

##A partir de ahora todas las requests que se hagan a la API DEBEN incluir headers=header
## Dado que usa self signed cert , tengo verify=False y deshabilito warings pero para produccion habria que arreglarlo


## Request para obtener informacion del usuario actual, asumo que deberia servir para keepAlive
#r2=requests.get(base_url+'/api/users/current',headers=header,verify=False)

## Crear Listeners
#id_listener=27
#covenant_dict={'useSSL':'false','urls':[current_ip],'name':'test-listener','guid':'guid','description':'description-string','bindAdress':'0.0.0.0','bindPort':80,'connectAddresses':[current_ip],'connectPort':80,'profileId':'2','listenerTypeId':'1','status':'Active','id':id_listener}
## El diccionario de arriba incluye 
## - Lo minimo y necesario para poder hacer el POST creando el listener
## - El id_listener no es necesario pero me es mas comodo definirlo yo antes que parsear la respuesta
## Los parametros se lo paso como un JSON
## Los valores para los ID son de 1 en adelante
#r3=requests.post(base_url+'/api/listeners/http',json=covenant_dict,headers=header,verify=False)

##Borrar Listeners
##Es un delete a /api/listeners/<idListener>
#r4=requests.delete(base_url+'/api/listeners/{}'.format(id_listener),headers=header,verify=False)


####### Get Launchers

#r5 = requests.get(base_url+'/api/launchers',headers=header,verify=False)

## El formato que devuelve es el siguiente

#get_launchers_models = json.loads( """
#  {
#    "id": 0,
#    "listenerId": 0,
#    "implantTemplateId": 0,
#    "name": "string",
#    "description": "string",
#    "type": "Wmic",
#    "dotNetVersion": "Net35",
#    "runtimeIdentifier": "win_x64",
#    "validateCert": true,
#    "useCertPinning": true,
#    "smbPipeName": "string",
#    "delay": 0,
#    "jitterPercent": 0,
#    "connectAttempts": 0,
#    "killDate": "2021-02-19T15:11:00.891Z",
#    "launcherString": "string",
#    "stagerCode": "string",
#    "outputKind": "ConsoleApplication",
#    "compressStager": true
#  }
#""")
