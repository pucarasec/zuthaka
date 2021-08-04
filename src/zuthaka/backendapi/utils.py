import datetime
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict
from .services import ClassHandlers
import inspect

def date_from_iso(date_string):
    '''
    Creates an Datetime object from a ISO 8601 formated string
    (necesary, in python previous 3.7)
    '''
    date_time, _, micro_seconds = date_string.partition(".")
    date_time = datetime.datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%S")
    micro_seconds = int(micro_seconds.rstrip("Z"), 10)
    return date_time + datetime.timedelta(microseconds=micro_seconds)

class CustomPageNumberPagination(PageNumberPagination):

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('current', self.page.number),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
         ]))


class EnablePartialUpdateMixin:

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


# collect all available classes to instantiation

def collect_classes(module, parent):
    async_methods = [ 'is_alive', 'get_listener_types', 'get_launcher_types', 'create_listener', 'delete_listener', 'create_launcher', 'download_launcher', 'retreive_agents', 'shell_execute']
    defined_classes = []
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, parent):
            if  obj != parent:
                defined_classes.append(obj)
    return defined_classes

def collect_handlers():
    handlers_module = []
    for  elem  in  dir(ClassHandlers):
        if inspect.ismodule(eval('ClassHandlers.'+elem)):
            handlers_module.append(eval('ClassHandlers.'+elem))
    return handlers_module
