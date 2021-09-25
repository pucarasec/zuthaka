import logging
import uuid
import json
import asyncio
import os

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile

from . import models
from .agent_ws import AgentWs

logger = logging.getLogger(__name__)
'''
 # Types of events:


 ## Shell   consistency > availability
   -command
    SEND
       - : {"type": "shell.execute", "command":"ls"}
    RECEIVE          
       - : {"type": "shell.result", "content": ["chat  db.sqlite3  manage.py  mysite"]}
       - : {"type": "shell.result", "error": "Agent not reachable"}

 ## Manage  consistency < availability
   - option: "delay_in_seconds"
   - value: "5"

 ## FileManager  consistency < availability
   -current_folder: "/abc/banana"
   -file_folder: ['file1', 'file2']
    SEND
       - : {"type": "file_manager.list_directory", "reference":"" "directory": ""}
       - : {"type": "file_manager.upload", "target_directory":"C:\\some_path", "reference":""}
       - : {"type": "file_manager.download", "file_path":"C:\\Users", "reference":""} 


       - : {'type': 'file_manager.execute'} ???
       - : {'type': 'file_manager.drives'}

    RECEIVE

       - : {"type": "file_manager.list_directory.result", "reference":"", "content":{"files":[{"file":"some_file1.txt", "additional_info":"rw-rw-r--  1 test test  13502 ene 14 17:50" }], "directories": []}}
       - : {"type": "file_manager.list_directory.result", "reference":"", "error": "Permission Denied"}


       - : {"type": "file_manager.upload.result", "reference":"", "content":"file uploaded"}
       - : {"type": "file_manager.upload.result", "reference":"", "error": "Permission Denied"}
       - : {"type": "file_manager.upload.result", "reference":"", "error": "Unable to retrive file. Please upload the file after generating a task"}

       - : {"type": "file_manager.download.result", "reference":"", "content":"file ready to download"}
       - : {"type": "file_manager.download.result", "reference":"", "error": "Permission Denied"}


        #TODO
       - : {'type': 'file_manager.execution', 'pid':'1234'}

 ## ProcessManager  consistency < availability
    SEND
       - : {'type': 'process_manager.inject',} // Modulo POST-EXPL ?? C2 Agnostic
       - : {'type': 'process_manager.terminate',}
       - : {'type': 'process_manager.list', 'parametro?paginacion?filtro?' : ''}
    RECEIVE          
       - : {'type': 'process_manager.list.result', 'content':[{'pid':'123', 'command':'someScript.py', 'permission': 'system' ,'ppid': 12 }]

 ## PostExploitation  consistency < availability
    SEND
       - : {'type': 'post_explotation.execute',  'options': [{'name1': 'value1'}], 'id_modulo': 999 }
       - : {'type': 'post_explotation.available', 'parametro?paginacion?filtro?' : ''}
    RECEIVE
       - : {'type': 'post_explotation.available.result', 'content':[{'name':'mimikatz_dump', 'c2_id':1, 'type':'windows/powershell', 'description':'dumps passowrds in memory', 'documentation':'/link', 'options': ', 'id_modulo': 999 }]
       - : {'type': 'post_explotation.result', 'content':"string", 'content_url' :'https://'} 
'''

@sync_to_async
def get_task(reference):
    task = models.AgentTask.objects.get(command_ref=reference)
    return task

@sync_to_async
def create_task():
    task = models.AgentTaskEvent.objects.create()
    return task

@sync_to_async
def get_task_file(task):
    logger.info("task accessing: %r", task)
    task_event = models.AgentTaskEvent.objects.get(task=task.pk)
    return task_event.transition_file

@sync_to_async
def complete_task(task):
    task.completed = True
    task.save()

@sync_to_async
def persist_transition_file(task, file_path, content):
    filename = os.path.basename(file_path)
    cf = ContentFile(content)
    task.transition_file.save(filename, cf)
    task.completed = True
    task.save()

@sync_to_async
def save_task_event(result):
    task.completed = True
    task.save()

@sync_to_async
def task_new():
    new_task = models.AgentTask.objects.create()
    return new_task

def require_task(func):
    async def task_tracking(*args):
        logger.info("task_tracking args:%r", args)
        try:
            reference = args[1].pop('reference')
            logger.debug("task reference:%r", reference)
            task = await get_task(reference)
            if not task.completed:
                logger.debug("func: %r", func)
                await func(*args, task)
            else:
                await args[0].send_json({'type': 'error',
                                         'content': 'Task already finalized. Task with reference {},\
                                          has already ended, please generate a new task'.format(args[1].get('reference'))})
        except ObjectDoesNotExist:
            await args[0].send_json({'type': 'error',
                                     'content': 'Invalid reference. No task has been registered with\
                                      reference {}'.format(args[1].get('reference'))})
        except KeyError as err:
            # logger.exception("error: %r", err)
            await args[0].send_json({'type': 'error', 'content': 'invalid event, task refrence needed'})
    return task_tracking

@sync_to_async
def get_agent_by_id(pk):
    agentDAO = models.Agent.objects.get(pk=pk)
    agent = AgentWs(agentDAO)
    return agent

class AgentConsumer(AsyncJsonWebsocketConsumer):
    unique_id = ""
    buffersize = 10240000
    port = 4444
    host = "0.0.0.0"

    async def connect(self):
        logger.debug("scope: %r", self.scope)
        if not self.scope['user'].is_authenticated:
            await self.close(code=403)

        self.agent_id = self.scope['url_route']['kwargs']['agent_id']
        self.agent_queue = 'agent_queue_{}'.format(self.agent_id)
        await self.channel_layer.group_add(self.agent_queue, self.channel_name)

        await self.accept()
        self.agent = await get_agent_by_id(self.agent_id)
        logger.info("Connected Agent: agent_queue:%r, agent_id:%r", self.agent_queue, self.agent_id)

    async def disconnect(self, close_code):
        logger.info("Disconnected Agent:%r, agent_queue:%r, agent_id:%r", self, self.agent_queue, self.agent_id)
        await self.channel_layer.group_discard(self.agent_queue, self.channel_name)

    @classmethod
    async def decode_json(cls, text_data):
        try:
            return json.loads(text_data)
        except json.JSONDecodeError:
            logger.error('Invalid json: %r', text_data) 
            return {'type':'invalid.event'}

    async def receive_json(self, event):
        logger.info('Agent:%s, Received: %s', self, event)
        await self.channel_layer.group_send(self.agent_queue, event)

    async def send_json(self, content, close=False):
        logger.info('Agent:%s, Sending: %s', self, content)
        await super().send_json(content, close=close)

    async def create_task(self, event):

        new_task = await task_new()
        await self.send_json({'type': 'task.created', 'reference': str(new_task.command_ref)})

    async def invalid_event(self, event):
        await self.send_json({'type':'error', 'content': 'invalid json received'})

    @require_task
    async def shell_execute(self, event, task):
        # {"type":"shell.execute", "command":"ls", "reference":""}
        result = await self.agent.shell_execute(event.get('command'))
        logger.debug('result: %r', repr(result))
        await complete_task(task)
        response = {'type': 'shell.execute.result',
                    'reference': task.command_ref}
        response.update(result)
        await self.send_json(response)

    @require_task
    async def file_manager_list_directory(self, event, task):
        # {"type": "file_manager.list_directory", "directory": "", "reference": ""}
        result = await self.agent.list_directory(event.get('directory'))
        logger.debug('result: %r', repr(result))
        await complete_task(task)
        response = {'type': 'file_manager.list_directory.result',
                    'reference': task.command_ref}
        response.update(result)
        logger.debug('response: %r', repr(response))
        await self.send_json(response)

    @require_task
    async def file_manager_upload(self, event, task):
        # {'type': 'file_manager.upload', 'target_directory':'C:\\some_path', "reference":"77777-aaaaaaaa-1111-33333333"}
        result = {}
        try:
            transition_file = await get_task_file(task)
            logger.info('Uploading transition_file: %r', transition_file)
            result = await self.agent.upload_file(transition_file, event.get('target_directory'))
        except Exception as e:
            logger.exception("testng")
            result = {
                'error': 'Unable to retrive file. Please upload the file after generating a task'}
        await complete_task(task)
        response = {'type': 'file_manager.upload.result',
                    'reference': task.command_ref}
        response.update(result)
        await self.send_json(response)

    @require_task
    async def file_manager_download(self, event, task):
        # {'type': 'file_manager.download', 'file_path':'C:\\Users'}
        file_path = event.get('file_path')
        file_bytes = await self.agent.download_file(file_path)
        await persist_transition_file(task, file_path, file_bytes)
        # await complete_task(task) # Task is not completed until downloaded
        response = {'type': 'file_manager.download.result',
                    'reference': task.command_ref}
        response.update({"content":"file ready to download"})
        await self.send_json(response)

    @require_task
    async def process_manager_list(self, event, task):
        # {"type": "file_manager.list_directory", "directory": "", "reference": ""}
        result = await self.agent.list_processes()
        logger.debug('result: %r', repr(result))
        await complete_task(task)
        response = {'type': 'process_manager.list.result',
                    'reference': task.command_ref}
        response.update(result)
        logger.debug('response: %r', repr(response))
        await self.send_json(response)

    @require_task
    async def process_manager_terminate(self, event, task):
        result = {}
        try:
            logger.info('...')
            result = await self.agent.process_terminate(event['pid'])
        except KeyError as e:
            result = {
                    'type': 'error',
                    'content': 'the process id should be specified in the "pid" attribute'}
        await complete_task(task)
        response = {'type': 'process_manager.terminate.result',
                    'reference': task.command_ref}
        response.update(result)
        await self.send_json(response)

    @require_task
    async def process_manager_inject(self, event, task):
        result = {}
        try:
            logger.info('...')
            result = await self.agent.process_inject(event['pid'])
        except KeyError as e:
            result = {
                    'type': 'error',
                    'content': 'the process id should be specified in the "pid" attribute'}
        await complete_task(task)
        response = {'type': 'process_manager.inject.result',
                    'reference': task.command_ref}
        response.update(result)
        await self.send_json(response)

    @require_task
    async def post_exploitation_available(self, event, task):
        result = await self.agent.post_exploitation_available()
        await complete_task(task)
        response = {'type': 'post_exploitation.available.result',
                    'reference': task.command_ref}
        response.update(result)
        print('OBTEINDED RESPONSE %r', response)
        await self.send_json(response)

    @require_task
    async def post_exploitation_execute(self, event, task):
        response = {'type': 'post_exploitation.execute.result.ok',
                    'reference': task.command_ref}
        # availables await self.agent.post_exploitation_available()
        result = await self.agent.post_exploitation_execute(event['id_module'], event.get('options', []))
        # save_task_event?
        response.update(result)
        await self.send_json(response)

        response = {'type': 'post_exploitation.execute.result.shell',
                    'reference': task.command_ref}
        result = await self.agent.post_exploitation_retrieve(event['id_module'], event.get('options', []))
        # save_task_event?
        await complete_task(task)
        if 'content_url' in result:
            result.update({'content_url':result['content_url'].format(self.agent_id, task.command_ref)})
        response.update(result)
        await self.send_json(response)

