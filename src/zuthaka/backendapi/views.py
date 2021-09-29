from django.shortcuts import get_object_or_404
from .filters import C2Filter, LauncherFilter, ListenerFilter
from .authentication import BearerAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from django_filters import rest_framework as filters
import os
import logging
logger = logging.getLogger(__name__)



from django.conf import settings
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
# Users views
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from django.core.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from .models import (C2, Agent, C2Type, Launcher, LauncherType, Listener,
                     ListenerType, AgentTask, AgentTaskEvent)
from .serializers import (AgentSerializer, C2Serializer, C2TypeSerializer,
                          LauncherSerializer, LauncherTypeSerializer,
                          ListenerSerializer, ListenerTypeSerializer,
                          UserSerializer, AgentTaskEventSerializer, AgentTaskSerializer,
                          AgentTaskSerializer2)
from rest_framework import serializers
from .utils import EnablePartialUpdateMixin

allowed_methods = ['get', 'post', 'put', 'patch', 'delete', 'head',
                   'options', 'trace'] if settings.DEBUG else ['get', 'post', 'put', 'delete']


# from .services.async_service import service # this might be a singleto
# from .apps.BackendapiConfig import service # this IS a singleto
from .services.async_service import ResourceExistsError, ResourceNotFoundError # this might be a singleto
from .services.async_service import Service

class C2sViewSet(ModelViewSet):
    '''
        Real Business Logic '''
    queryset = C2.objects.all()
    serializer_class = C2Serializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = C2Filter

    def perform_create(self, serializer):
        service = Service.get_service()
        dto = serializer.to_dto()
        try:
            is_alive  = async_to_sync(service.isalive_c2)(dto)
            if is_alive:
                # result = self.persist_db(dto)
                serializer.save()
                # return Resonse(result, status = status.HTTP_201_CREATED)
            else:
                from rest_framework import exceptions
                raise exceptions.NotAcceptable(detail={"error":"the c2 is not accepting the given options"})
        except ConnectionRefusedError as err:
            # network unreachable
            raise serializers.ValidationError("The c2 rejected the connection")
        except ConnectionError as err:
            # network unreachable
            raise serializers.ValidationError("The c2 was not reachable")
        except ValueError as err:
            # Invalid options
            # raise serializers.ValidationError("the options provided to the service are not processabel")
            raise serializers.ValidationError(*err.args)

# TypeModelMixin ? should be collected on start of the applications
    @action(detail=False, methods=['get'])
    def types(self, request):
        queryset = C2Type.objects.all().order_by('id')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = C2TypeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = C2TypeSerializer(queryset, many=True)
        return Response(serializer.data)


class ListenersViewSet(ModelViewSet):
    '''
        Real Business Logic
    '''
    queryset = Listener.objects.all()
    serializer_class = ListenerSerializer
    http_method_names = allowed_methods
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = ListenerFilter

    authentication_classes = [BearerAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]


    @action(detail=False, methods=['get'])
    def types(self, request):
        queryset = ListenerType.objects.all().order_by('id')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ListenerTypeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ListenerTypeSerializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        service = Service.get_service()
        dto = serializer.to_dto()
        try:
            _listener_created = async_to_sync(service.create_listener)(dto)
            serializer.save(listener_internal_id = _listener_created['listener_internal_id'])
        except ResourceExistsError:
            raise serializers.ValidationError("ResourceExistsError: Unable to create Listener because resource is in use")
        except ConnectionError:
            raise serializers.ValidationError("The c2 was not reachable")
        except ValueError as err:
            raise serializers.ValidationError(*err.args)

    def perform_destroy(self, instance):
        service = Service.get_service()
        dto = self.serializer_class.to_dto_from_instance(instance)
        try:
            import ipdb; ipdb.set_trace()
            listener_internal_id = async_to_sync(service.delete_listener)(dto)
            instance.delete()
        except ValueError as err:
            # Malformed DTO
            logger.error(err)
            raise serializers.ValidationError(*err.args)
        except ResourceNotFoundError:
            # Inconsistency. to be soft erased
            pass
        except ConnectionError:
            # network unreachable
            pass


class LaunchersViewSet(EnablePartialUpdateMixin, ModelViewSet):
    '''

    This class is in charge of  handling all the views of Listeners in the API.

    '''
    queryset = Launcher.objects.all()
    serializer_class = LauncherSerializer
    http_method_names = allowed_methods
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = LauncherFilter

    authentication_classes = [BearerAuthentication, SessionAuthentication]
    # permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def types(self, request):
        queryset = LauncherType.objects.all().order_by('id')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = LauncherTypeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = LauncherTypeSerializer(queryset, many=True)
        return Response(serializer.data)


    def perform_create(self, serializer):
        service = Service.get_service()
        dto = serializer.to_dto()
        try:
            launcher_created_dto = async_to_sync(service.create_launcher_and_retrieve)(dto)
            logger.error("launcher_created_dto: %r", launcher_created_dto)
            validated_data = serializer.validated_data
            new_launcher = serializer.save(listener=validated_data['listener'],launcher_type=validated_data['launcher_type'],launcher_internal_id = launcher_created_dto['launcher_internal_id'])
            new_launcher.launcher_file.save(launcher_created_dto['payload_name'],ContentFile(launcher_created_dto['payload_content']), save=True)
            # data =  serializer.validated_data 
        except ValueError:
            raise serializers.ValidationError("The c2 was not reachable")
        except ConnectionError:
            raise serializers.ValidationError("The c2 was not reachable")

    @action(detail=True, methods=['get'])
    def download(self, request, pk):
        detail = Launcher.objects.get(pk=pk)
        response = HttpResponse(detail.launcher_file.file,
                                content_type='application/octet-stream')
        filename = os.path.basename(detail.launcher_file.name)
        response['Content-Disposition'] = 'attachment; filename={}'.format( filename)
        return response

# DestroyModelMixin ?It makes sense in the future handle infrastructure
    def destroy(self, request, pk=None):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        service = Service.get_service()

        service = Service.get_service()
        dto = self.serializer_class.to_dto_from_instance(instance)
        try:
            listener_internal_id = async_to_sync(service.delete_launcher)(dto)
            instance.delete()
        except ValueError:
            # Malformed DTO
            pass
        except ResourceNotFoundError:
            # Inconsistency. to be soft erased
            pass
        except ConnectionError:
            # network unreachable
            pass



class AgentsViewSet(ModelViewSet):
    '''

    This class is in charge of  handling all the views of Listeners in the API.

    '''
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    authentication_classes = [BearerAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        service = Service.get_service()
        dto = AgentSerializer.to_dto()
        try:
            # print(dto)
            agents  = async_to_sync(service.retrieve_agents)(dto)
            logger.info("agents retrieved by service: %r", agents)
            # validation for new agents is needed
            new_agents = []
            for agent in agents['agents']:
                _c2_id = agent.get('c2_id')
                old_agent = Agent.objects.filter(c2_id=_c2_id, internal_id = agent.get('internal_id'))
                logger.debug("old agents: %r", old_agent)
                if not old_agent:
                    new_agent = {}
                    new_agent.update(agent)
                    new_agent['c2'] = agent.get('c2_id')
                    new_agent['listener'] = agent.get('listener_id')
                    new_agents.append(new_agent)
                else:
                    _old_agent = old_agent[0]
                    persisted_agent = AgentSerializer(_old_agent, data=agent, partial=True)
                    _is_valid = persisted_agent.is_valid()
                    # import ipdb;ipdb.set_trace()
                    persisted_agent.save()
            persisted_agent = AgentSerializer(data=new_agents, many=True)
            _is_valid = persisted_agent.is_valid()
            data = persisted_agent.data
            persisted_agent.save()

            result = super().list(self, request)
            return result
        except ConnectionRefusedError as err:
            # network unreachable
            raise serializers.ValidationError("The c2 rejected the connection")
        except ConnectionError as err:
            # network unreachable
            raise serializers.ValidationError("The c2 was not reachable")
        except ValueError as err:
            # Invalid options
            # raise serializers.ValidationError("the options provided to the service are not processabel")
            raise serializers.ValidationError(*err.args)


    @action(detail=True, methods=['post'])
    def upload(self, request, pk=None):
        try:
            task_reference = request.data.get('task-reference')
            if not task_reference:
                return Response({'detail': 'task-reference required'}, status=status.HTTP_400_BAD_REQUEST)
            task = AgentTask.objects.get(command_ref=task_reference)
            transition_file = request.data.get('file')
            if not transition_file:
                return Response({'detail': 'file required'}, status=status.HTTP_400_BAD_REQUEST)
            serializer = AgentTaskEventSerializer(
                data={'task': task.pk, 'transition_file': transition_file})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except AgentTask.DoesNotExist:
            return Response({'detail': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        try:
            task_reference = request.query_params.get('task-reference')
            if not task_reference:
                return Response({'detail': 'task-reference required'}, status=status.HTTP_400_BAD_REQUEST)
            task = AgentTask.objects.get(command_ref=task_reference)
            # is this necessary? 
            # if task.completed:
            #     return Response({'detail': 'Task already completed'}, status=status.HTTP_400_BAD_REQUEST)

            # task.completed = True
            # task.save()
            # a simple mock
            # detail = Launcher.objects.get(pk=1)
            # file_transfered = open('./files/screenshot.jpg', 'rb')
            # _file = ContentFile(file_transfered.read())

            response = HttpResponse(task.transition_file.file,
                                    content_type='application/octet-stream')
            # filename = os.path.basename(detail.launcher_file.name)
            response['Content-Disposition'] = 'attachment; filename={}'.format(
                task.transition_file.name)
            return response
        except AgentTask.DoesNotExist:
            return Response({'detail': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)


class TasksViews(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    '''
    '''
    authentication_classes = [BearerAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = AgentTask.objects.all()
    serializer_class = AgentTaskSerializer2

from rest_framework.views import APIView
class ChangePassword(APIView):
    authentication_classes = [BearerAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
            user = request.auth.user
            password = request.data.get('password')
            if not password:
                return Response({'detail': 'password missing'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                validate_password(password)
            except ValidationError as errors:
                return Response(errors, status=status.HTTP_412_PRECONDITION_FAILED)
            user.set_password(password)
            user.save()
            return Response(user.id, status.HTTP_201_CREATED)

class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    http_method_names = allowed_methods

    authentication_classes = [BearerAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=False)
        user = User.objects.filter(Q(username=request.data['username']) | Q(
            username=request.data['email'])).count()
        if user == 0:
            try:
                errors = validate_password(request.data['password'])
            except ValidationError:
                return Response(errors, status=status.HTTP_412_PRECONDITION_FAILED)
                user = User.objects.create_user(
                    request.data['username'], request.data['email'], request.data['password'])
        else:
            return Response("Username or email already exists.", status=status.HTTP_409_CONFLICT)
        user.save()
        return Response(user.id, status.HTTP_201_CREATED)
