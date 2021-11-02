from rest_framework import serializers
from .models import C2
from .models import C2Option
from .models import C2Type
from .models import C2TypeOption
from .models import Listener
from .models import ListenerOption
from .models import ListenerType
from .models import ListenerTypeOption
from .models import Launcher
from .models import LauncherOption
from .models import LauncherType
from .models import LauncherTypeOption
from .models import Agent
from .models import Project
from .models import AgentTask
from .models import AgentTaskEvent
from django.contrib.auth.models import User

from .dtos import C2Dto, ListenerDto, LauncherDto, RequestDto, C2InstanceDto


# C2
class C2TypeOptionSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='field_type')

    class Meta:
        model = C2TypeOption
        fields = ('name', 'example', 'description', 'type', 'required')


class C2TypeSerializer(serializers.ModelSerializer):
    options = C2TypeOptionSerializer(many=True)

    class Meta:
        model = C2Type
        fields = ('id', 'name', 'description', 'documentation', 'options')


class AgentTaskSerializer(serializers.ModelSerializer):
    # events = AgentTaskEventSerializer(many=True)

    class Meta:
        model = AgentTask
        # fields = ('id', 'creation_date', 'command_ref', 'completed','events')
        fields = ('id', 'creation_date', 'command_ref', 'completed')


class AgentTaskEventSerializer(serializers.ModelSerializer):
    task = serializers.PrimaryKeyRelatedField(queryset=AgentTask.objects.all())
    class Meta:
        model = AgentTaskEvent
        #fields = ('id', 'transition_file')
        fields = ('id','task', 'content', 'transition_file')

class AgentTaskSerializer2(serializers.ModelSerializer):
    events = AgentTaskEventSerializer(many=True)

    class Meta:
        model = AgentTask
        fields = ('id', 'creation_date', 'command_ref', 'completed','events')
        # fields = ('id', 'creation_date', 'command_ref', 'completed')

class C2OptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = C2Option
        fields = ('name', 'value')


class C2Serializer(serializers.ModelSerializer):
    options = C2OptionSerializer(many=True)

    class Meta:
        model = C2
        fields = ('id', 'c2_type', 'creation_date', 'options')
        read_only_fields = ('creation_date',)

    def create(self, validated_data):
        options = validated_data.pop('options', [])
        c2_instance = C2.objects.create(**validated_data)
        for option in options:
            c2_option = C2Option.objects.create(c2=c2_instance, **option)
        return c2_instance

    def update(self, instance, validated_data):
        new_options = validated_data.pop('options', [])
        if validated_data:
            instance.__dict__.update(**validated_data)
        for option in new_options:
            current_option = instance.options.filter(
                name=option.get('name'))[0]
            if current_option:
                current_option.__dict__.update(**option)
            else:
                current_option = C2Option.objects.create(c2=instance, **option)
            current_option.save()
        instance.save()
        return instance

    def to_dto(self):
        '''
        { 'c2_type' :'EmpireC2Type',
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
            ]
        }
        '''
        data = self.validated_data 
        # logger.debug('data: %r', data)
        # dto = {}
        # if 'c2_type' in data:
        #     dto['c2_type'] = data['c2_type'].name
        # if 'options' in data:
            # dto['c2_options'] = {elem['name']:elem['value'] for elem in data['options']}
        options = {elem['name']:elem['value'] for elem in data['options']}
        _c2_type = data['c2_type'].name
        c2_dto = C2Dto(c2_type= _c2_type, options=options)
        dto = RequestDto(c2 = c2_dto)
        return dto

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

# Listeners

class ListenerTypeOptionSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='field_type')
    class Meta:
        model = ListenerTypeOption
        fields = ('name', 'example', 'description', 'type', 'required')

class C2sAvaialbleField(serializers.RelatedField):
    def to_representation(self, value):
        c2s_available = C2.objects.all().filter(c2_type_id=value.id)
        return [{'c2_id': c2.id, 'name': c2.c2_type.name} for c2 in c2s_available]

class ListenerTypeSerializer(serializers.ModelSerializer):
    options = ListenerTypeOptionSerializer(many=True)
    available_c2s = C2sAvaialbleField(source='c2_type', read_only=True)
    # available_c2s = C2Serializer(source='c2_type',read_only=True)

    class Meta:
        model = ListenerType
        fields = ('id', 'name', 'available_c2s', 'description',  'options')

class ListenerOptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ListenerOption
        fields = ('name', 'value')

class ListenerSerializer(serializers.ModelSerializer):
    options = ListenerOptionSerializer(many=True)
    c2_id = serializers.PrimaryKeyRelatedField(
        source='c2', queryset=C2.objects.all(), read_only=False)
    # listener_type_id = serializers.PrimaryKeyRelatedField(source='listener_type',queryset=LauncherType.objects.all(),read_only=False)

    class Meta:
        model = Listener
        fields = ('id', 'c2_id', 'listener_type', 'creation_date', 'options', 'listener_internal_id')
        read_only_fields = ('creation_date',)

    def create(self, validated_data):
        options = validated_data.pop('options', [])
        listener_instance = Listener.objects.create(**validated_data)
        for option in options:
            listener_option = ListenerOption.objects.create(
                listener=listener_instance, **option)
        return listener_instance

    def update(self, instance, validated_data):
        new_options = validated_data.pop('options', [])
        instance.__dict__.update(**validated_data)
        for option in new_options:
            current_option = instance.options.filter(name=option.get('name'))
            if current_option:
                current_option.__dict__.update(**option)
            else:
                listener_option = ListenerOption.objects.create(
                    listener=instance, **option)
        instance.save()
        return instance

    def to_dto(self):
        '''
        {
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

        '''
        data = self.validated_data 
        dto = {}
        try:
            # _c2_type = data['c2_type'].name
            _c2_type = data['c2'].c2_type.name
            options = {option.name: option.value for option in data['c2'].options.all()}
            c2_dto = C2Dto(c2_type= _c2_type, options=options)
            
            listener_type = data['listener_type'].name
            listener_options = {elem['name']: elem['value'] for elem in data['options']}
            listener_dto = ListenerDto(listener_type=listener_type, options=listener_options)
            
            dto = RequestDto(c2=c2_dto, listener=listener_dto)
            # dto['c2_type'] = data['c2'].c2_type.name
            # dto['c2_options'] = {option.name:option.value for option in data['c2'].options.all()}
            # dto['listener_type'] = data['listener_type'].name
            # dto['listener_options'] = {elem['name']:elem['value'] for elem in data['options']}
        except KeyError as err:
            raise serializers.ValidationError(repr(err))
        return dto

    @classmethod
    def to_dto_from_instance(self, instance):
        '''
        dto = {
        'c2_type' :'CovenantC2Type',
        'c2_options': { 
            "url": "https://127.0.0.1:7443" ,
            "username": "cobbr",
            "password": "NewPassword!"
                }
        'listener_type' :'CovenantHTTPListenerType',
        'listener_internal_id' :'123456',
        }
        '''
        try:
            # _c2 = C2.objects.get(pk=instance.c2_id)

            # c2_type = _c2.c2_type.name
            # c2_options = {option.name:option.value for option in _c2.options.all()}
            # listener_type = instance.listener_type.name
            # listener_options = {elem.name:elem.value for elem in instance.options.all()}
            # listener_internal_id = instance.listener_internal_id
            
            _c2 = C2.objects.get(pk=instance.c2_id)
            _c2_type = _c2.c2_type.name
            options = {option.name: option.value
                       for option in _c2.options.all()}
            c2_dto = C2Dto(c2_type= _c2_type, options=options)
            
            listener_type = instance.listener_type.name
            listener_options = {option.name: option.value
                                for option in instance.options.all()}
            listener_internal_id = instance.listener_internal_id
            listener_dto = ListenerDto(
                listener_type=listener_type,
                options=listener_options,
                listener_internal_id=listener_internal_id
            )

            dto = RequestDto(c2= c2_dto, listener=listener_dto)
            # _c2 = C2.objects.get(pk=instance.c2_id)
            # dto['c2_type'] = _c2.c2_type.name
            # dto['c2_options'] = {option.name:option.value for option in _c2.options.all()}
            # dto['listener_type'] = instance.listener_type.name
            # dto['listener_options'] = {elem.name:elem.value for elem in instance.options.all()}
            # dto['listener_internal_id'] = instance.listener_internal_id
        except KeyError as err:
            raise serializers.ValidationError(repr(err))
        return dto

# Launcher serializers
class LauncherTypeOptionSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='field_type')
    class Meta:
        model = LauncherTypeOption
        fields = ('name', 'example', 'description', 'type', 'required')


class ListenersAvailableField(serializers.RelatedField):
    def to_representation(self, value):
        c2s = C2.objects.all().filter(c2_type=value)
        listeners_available = []
        for c2 in c2s:
            listeners_available.extend(Listener.objects.all().filter(c2=c2))
        response = [{'listener_id': listener.id,
                    'listener_type': listener.listener_type.name} for
                    listener in listeners_available]
        return response


class LauncherTypeSerializer(serializers.ModelSerializer):
    options = LauncherTypeOptionSerializer(many=True)
    available_listeners = ListenersAvailableField(
        source='c2_type', read_only=True)

    class Meta:
        model = ListenerType
        fields = ('id', 'name', 'available_listeners',
                  'description',  'options')


class LauncherOptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = LauncherOption
        fields = ('name', 'value')


class LauncherSerializer(serializers.ModelSerializer):
    options = LauncherOptionSerializer(many=True)
    listener_id = serializers.PrimaryKeyRelatedField(
        source='listener', queryset=Listener.objects.all(), read_only=False)
    file_name =  serializers.SerializerMethodField()
    # launcher_type_id = serializers.PrimaryKeyRelatedField(source='launcher_type',queryset=LauncherType.objects.all(),read_only=False)

    class Meta:
        model = Launcher
        fields = ('id', 'listener_id', 'launcher_type', 
                  'creation_date', 'options', 'file_name')
        read_only_fields = ('creation_date', 'file_name')

    def get_file_name(self, obj):
        return obj.launcher_file.name

    def create(self, validated_data):
        options = validated_data.pop('options', [])
        launcher_instance = Launcher.objects.create(**validated_data)
        for option in options:
            launcher_option = LauncherOption.objects.create(
                launcher=launcher_instance, **option)
        return launcher_instance

    def update(self, instance, validated_data):
        new_options = validated_data.pop('options', [])
        instance.__dict__.update(**validated_data)
        for option in new_options:
            current_option = instance.options.filter(name=option.get('name'))
            if current_option:
                current_option.__dict__.update(**option)
            else:
                launcher_option = LauncherOption.objects.create(
                    launcher=instance, **option)
        instance.save()
        return instance


    def to_dto(self):
        '''
        dto = {
        'c2_type' :'CovenantC2Type',
        'c2_options': {
                "url": "https://127.0.0.1:7443",
                "username": "cobbr",
                "password": "NewPassword!"
            },
          'listener_type' :'http',
          'listener_internal_id' :'123456',
          'listener_options' : {
                "interface": "192.168.0.1",
                "port": "139",
                "default_delay": "10",
            }
          'launcher_type' :'powershell',
          'launcher_options' : {
                "default_delay": "10"
            }
        }

        '''
        data = self.validated_data 
        try:
            # dto['c2_type'] = data['listener'].c2.c2_type.name
            # dto['c2_options'] = {option.name:option.value for option in data['listener'].c2.options.all()}
            # dto['listener_type'] = data['listener'].listener_type.name
            # dto['listener_type'] = data['listener'].listener_type.name
            # dto['listener_internal_id'] = data['listener'].listener_internal_id
            # dto['launcher_type'] = data['launcher_type'].name
            # dto['launcher_options'] = {elem['name']:elem['value'] for elem in data['options']}

            _c2_type = data['listener'].c2.c2_type.name
            options =  {option.name: option.value for option in data['listener'].c2.options.all()}
            c2_dto = C2Dto(c2_type=_c2_type, options=options)
            
            listener_type = data['listener'].listener_type.name
            listener_options = {option.name: option.value for option in data['listener'].options.all()}
            listener_dto = ListenerDto(listener_type=listener_type, options=listener_options)
            
            launcher_type = data['launcher'].launcher_type.name
            launcher_options = {option.name: option.value for option in data['launcher'].options.all()}
            launcher_dto = LauncherDto(launcher_type=launcher_type, options=launcher_options)

            dto = RequestDto(c2= c2_dto, listener=listener_dto, launcher=launcher_dto)
        except KeyError as err:
            raise serializers.ValidationError(repr(err))
        return dto


class AgentSerializer(serializers.ModelSerializer):
    # options = ListenerOptionSerializer(many=True)

    class Meta:
        model = Agent
        fields = ('id', 'c2', 'listener', 'first_conection', 'last_conection', 'username', 'hostname', 'internal_id', 'shell_type', 'active')
        # read_only_fields = ('id', 'c2', 'listener', 'creation_date',
        #                     'first_conection', 'last_conection', 'username', 'hostname')

    def c2_instances_dto():
        '''

        dto = {'c2s_intances':[{
            'c2_type' :'EmpireC2Type',
            'c2_id' : 1,
            'c2_options': {
                    "url": "https://127.0.0.1:7443",
                    "username": "cobbr",
                    "password": "NewPassword!"
                },
              'listeners_internal_ids' : {1:'1',2:'2',3:'3'} 
              }]}

        '''
        listeners = Listener.objects.all()
        c2s = {listener.c2 for listener in listeners}
        try:
            instances = []
            for c2 in c2s:
                c2_type = c2.c2_type.name
                c2_id = c2.id
                c2_options = {option.name:option.value for option in c2.options.all()}
                listener_ids = {listener.listener_internal_id: listener.id for listener in listeners if listener.c2 == c2} # keys are  the c2's internal ids  and values  are Zuthakas' ids
                c2_instance = C2InstanceDto(c2_type=c2_type, c2_id=c2_id, options= c2_options, listener_ids = listener_ids)
                instances.append(c2_instance)
            dto = RequestDto(c2_instances=instances)
        except KeyError as err:
            raise serializers.ValidationError(repr(err))
        return dto

    @classmethod
    def to_dto_from_instance(self, instance):
        '''
        dto = {
        'c2_type' :'CovenantC2Type',
        'c2_options': { 
            "url": "https://127.0.0.1:7443" ,
            "username": "cobbr",
            "password": "NewPassword!"
                }
        'listener_type' :'CovenantHTTPListenerType',
        'listener_internal_id' :'123456',
        }
        '''
        
        dto = {}
        try:
            _c2 = C2.objects.get(pk=instance.c2_id)

            _c2_type = _c2.c2_type.name
            options = {option.name:option.value for option in _c2.options.all()}
            c2_dto = C2Dto(c2_type= _c2_type, options=options)
            
            _listener = Listener.objects.get(pk=instance.listener_id)
            listener_type = _listener.listener_type.name
            listener_options = {elem.name:elem.value for elem in _listener.options.all()}
            listener_internal_id = _listener.listener_internal_id
            listener_dto = ListenerDto(listener_type= listener_type, options = listener_options, listener_internal_id=listener_internal_id)

            agent_internal_id = instance.internal_id
            agent_shell_type = instance.shell_type
            shell_dto = ShellExecuteDto(agent_internal_id=agent_internal_id, shell_type=shell_type)

            dto = RequestDto(c2= c2_dto, listener= listener, shell_execute=shell_dto)

            # _c2 = C2.objects.get(pk=instance.c2_id)
            # dto['c2_type'] = _c2.c2_type.name
            # dto['c2_options'] = {option.name:option.value for option in _c2.options.all()}

            # _listener = Listener.objects.get(pk=instance.listener_id)
            # dto['listener_type'] = _listener.listener_type.name
            # dto['listener_options'] = {elem.name:elem.value for elem in _listener.options.all()}
            # dto['listener_internal_id'] = _listener.listener_internal_id
            # dto['agent_internal_id'] = instance.internal_id
            # dto['agent_shell_type'] = instance.shell_type

        except KeyError as err:
            raise serializers.ValidationError(repr(err))
        return dto

# Projects

class ProjectSerializer(serializers.ModelSerializer):
    admins=UserSerializer(many=True)
    operators=UserSerializer(many=True)
    viewers=UserSerializer(many=True)

    class Meta:
        model=Project
        fields=('id', 'name', 'description', 'update_date',
                  'admins', 'operators', 'viewers')
