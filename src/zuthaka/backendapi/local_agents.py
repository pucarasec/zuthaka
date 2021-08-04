import asyncio
import shlex
import datetime

from asgiref.sync import sync_to_async

from . import models

import logging
logger = logging.getLogger(__name__) 

class LocalAgent():
    '''
    A simple implementation of the agent, that runs on the local server
    DO NO USE IN PRODUCTION is only for backend api definition porpuses
    '''

    def __init__(self, agentDAO):
        self.agent = agentDAO

    async def execute(self, cmd):
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        stdout, stderr = await proc.communicate()
        logger.debug("stdout:%r, stderr:%r", stdout, stderr)
        result = {}
        if stdout:
            result['content'] = stdout.decode('utf-8')
        else:
            result['error'] = stderr.decode('utf-8')
        logger.debug ("result:%r", result)
        return result

    async def list_directory(self, directory):
        shell_listing_dictionary = {
            "bash": " ls -AlL --time-style=long-iso {}",
            "powershell": "..."
        }
        command = shell_listing_dictionary['bash'].format(directory)
        logger.debug("command:%r", command)
        response = await self.execute(command)
        logger.debug("response:%r", response)
        content = response.get('content')
        if content:
            result = content.splitlines()
            logger.debug("result:%r", result)
            parsed_result = {'files': [], 'directories': []}
            for element in result[1:]:
                element_info = element.split()
                _date = ' '.join((element_info[5], element_info[6]))
                date = datetime.datetime.strptime(_date, '%Y-%m-%d %H:%M')
                if element_info[0].startswith('d'):
                    parsed_result['directories'].append(
                        {'name': element_info[-1], 
                            'date' :date.isoformat(),
                          'additional_info': element})
                else:
                    parsed_result['files'].append(
                            {'name': element_info[-1],
                             'size': element_info[4], 
                            'date' : date.isoformat(),
                             'additional_info': element})

            response['content'] = parsed_result
        return response

    async def upload_file(self, transition_file, target_directory):
        response = {}
        try:
            directory = target_directory + '/' + transition_file.name
            logger.debug("directory:%r", directory)
            with open(directory, 'wb') as created_file:
                created_file.write(transition_file.read())
            response = {'content': "file uploaded"}
        except Exception as e:
            logger.exception("error: %r", e)
            # add more specific errors
            response = {'error': "Permission denied"}
        return response

    async def download_file(self, file_path):
        response = {}
        try:
            with open(file_path) as created_file:
                response = {'content': "file ready to download"}
        except Exception as e:
            logger.exception("error: %r", e)
            # add more specific errors
            response = {'error': "Permission denied"}
        return response

    async def list_processes(self):
        shell_processes_listing = {
            "bash": "ps aux",
            "powershell": "..."
        }
        command = shell_processes_listing['bash']
        logger.debug("command:%r", command)
        response = await self.execute(command)
        logger.debug("response:%r", response)
        content = response.get('content')
        if content:
            result = content.splitlines()
            logger.debug("result:%r", result)
            parsed_result = []
            for element in result[1:]:
                element_info = element.split()
                parsed_result.append(
                        {'name': element_info[-1], 'permission': element_info[0], 'pid': element_info[1], 'additional_info': element})
            response['content'] = parsed_result
        return response

    async def process_terminate(self, pid):
        isinstance(pid, int) # to do safety check
        shell_processes_listing = {
            "bash": "kill {}",
            "powershell": "..."
        }
        command = shell_processes_listing['bash'].format(pid)
        logger.debug("command:%r", command)
        # Local handling is  exceptued
        return {'content': 'process terminated'}

    async def process_inject(self, pid):
        isinstance(pid, int) # to do safety check
        shell_processes_listing = {
            "bash": "kill {}",
            "powershell": "..."
        }
        command = shell_processes_listing['bash'].format(pid)
        logger.debug("command:%r", command)
        return {'content': 'Functionality not implemented'}

    async def post_exploitation_available(self):
        available_list = [{
            'name':'portScan',  
            'description':'Scan the target host for open ports', 
            'options_description':[
                    {
                    'name':'target',
                    'type': 'string',
                    'default_value':'127.0.0.1',
                    'description': 'Target to scan for open ports',
                    'example':'192.168.0.1',
                    'required':True
                    },
                    {
                    'name':'ports',
                    'type': 'string',
                    'default_value':'80,443,8080,8443',
                    'description': 'Ports to scan on the target',
                    'example':'1-65535',
                    'required':True
                    }
                ],
            'id_module': 1 },
{
            'name':'screenshot',  
            'description':'take screenshot of the current user', 
            'options_description':[],
            'id_module': 2 }
            ] 
        return {'content': available_list}

    async def post_exploitation_execute(self, id_module, options):
        #isinstance(pid, int) # to do safety check
        modules = {1:(('target','ports'), {'content': 'Started PortScan' }),
                2: ((),{'content':'Started screenshot'})
                }
        if id_module not in modules:
            return {"type": "post_exploitation.execute.result.error", "content": "id_module not valid"}
        for  required_option in  modules[id_module][0]:
            if  required_option not in options:
                return {"type": "post_exploitation.execute.result.error", "content": "missing required option: {}".format(required_option)}
        return modules[id_module][1]

    async def post_exploitation_retrieve(self, id_module, options):
        content_1 = 'ComputerName   Port  IsOpen \
------------   ----  ------ \
192.168.0.245  3000  True'
        modules = {1:(('target','ports'), {'header': 'portScan', 'content': content_1 }),
                2: ((),{'header': 'screenshot', 'content_url':'http://127.0.0.1/agents/{}/download?task={}'})
                }
        if id_module not in modules:
            return {"type": "post_exploitation.execute.result.error", "content": "id_module not valid"}
        return modules[id_module][1]

class Service():
    '''
    The functionality to retrive an agent that can consume corresponding events
    '''
    @sync_to_async
    def get_agent_by_id(self, pk):
        agentDAO = models.Agent.objects.get(pk=pk)
        agent = LocalAgent(agentDAO)
        return agent


##### Aca EMPIEZAN LOS PARSER DE LS Y CMD
import csv
import re
import datetime
import pprint

# Comandos para generar el texto a parsear
# En CMD
# dir /-c/q/a/o/t:w/n
# Te devuelve en hora local , para obtener la tz de la maquina infectada correr el siguiente comanda
# systeminfo | findstr  /C:”Time Zone”
# tasklist /v /FO:CSV
# Powershell
# gci -Force  | Select-Object Mode,LastWriteTimeUtc, Length, Name | ConvertTO-CSV -NoTypeInformation
# Get-Process -IncludeUserName | Sort-Object Id | Select-Object UserName, Id, CPU,HasExited, StartTime, ProcessName | ConvertTo-CSV -NoTypeInformation
# Se necesita admin por el flag -Includeusername que devuelve el owner del proceso
# Cada funcion recibe como primer parametro una lista de strings y los siguientes parametros listas de strings de parametros extras que pueden necesitar o no


def parsearLSCMD(texto_a_parsear, tz):
    file_list = []
    dir_list = []
    tz = re.search(r"(-+)+(.){5,5}", tz[0])  # Me devuelve el +- numero
    line_re = r"(.{10,10})[ ]{2}(.{8,8})[ ]+([<].+[>]|\d+)[ ]+([^\\]+)([^ ]+)[ ]+(.+)"
    for line in texto_a_parsear[5:-3]:  # Saco las lineas que no me interesan
        splitted_line = re.search(line_re, line)
        date_time_plus_timezone = (
            splitted_line.groups()[0]
            + " "
            + splitted_line.groups()[1]
            + " "
            + tz.group()
        )
        current_dict = {
            "additional_info": line,
            "name": splitted_line.groups()[5],
            "date": (
                datetime.datetime.strptime(
                    date_time_plus_timezone, "%m/%d/%Y  %I:%M %p %z"
                )
            ).isoformat(),
        }
        if "<" not in splitted_line.groups()[2]:  # Es un archivo con tamaño en bytes
            current_dict["size"] = splitted_line.groups()[2]
            file_list.append(current_dict)
        else:
            dir_list.append(current_dict)

    return [dir_list, file_list]


def parsearPSCMD(texto_a_parsear):
    result = []
    reader = csv.DictReader(texto_a_parsear)
    for row in reader:
        current_dict = {
            "name": row["Image Name"],
            "pid": row["PID"],
            "permission": row["User Name"],
            "additional_info": " ".join(row.values()),
        }
        result.append(current_dict)
    return result


def parsearLSPowershell(texto_a_parsear):
    dir_list = []
    file_list = []
    reader = csv.DictReader(texto_a_parsear)
    datetime_format = "%m/%d/%Y  %I:%M:%S %p %z"
    # Antes de parsear , hay que agregar la tz
    for row in reader:
        date_time_plus_timezone = row["LastWriteTimeUtc"] + " +00:00"
        date_time_plus_timezone = datetime.datetime.strptime(
            date_time_plus_timezone, datetime_format
        ).isoformat()
        current_row_dict = {
            "name": row["Name"],
            "date": date_time_plus_timezone,
            "additional_info": (" ".join(row.values())),
        }
        if row["Length"] != "":  # Es un archivo y tiene bytes
            current_row_dict["size"] = int(row["Length"])
            file_list.append(current_row_dict)
        else:
            dir_list.append(current_row_dict)
    return [dir_list, file_list]


def parsearPSPowershell(texto_a_parsear):
    result = []
    reader = csv.DictReader(texto_a_parsear)
    for row in reader:
        current_dict = {
            "name": row["ProcessName"],
            "pid": row["Id"],
            "permission": row["UserName"],
            "additional_info": " ".join(row.values()),
        }
        result.append(current_dict)
    return result


# # Abro archivos
# file_ls_cmd = open("./cmd_ls.txt", "r")
# file_ls_powershell = open("./powershell_ls.txt", "r")
# file_ps_cmd = open("./cmd_ps.txt", "r")
# file_ps_powershell = open("./powershell_ps.txt", "r")
# file_tz = open("./tz_info.txt", "r")

# # Genero las listas de strings
# list_ls_cmd = file_ls_cmd.read().splitlines()
# list_ls_powershell = file_ls_powershell.read().splitlines()
# list_ps_cmd = file_ps_cmd.read().splitlines()
# list_ps_powershell = file_ps_powershell.read().splitlines()
# list_tz = file_tz.read().splitlines()


# # Pruebo las funciones
# # Vamos primero con CMD.exe
# print("Parsear LS de CMD")
# pprint.pprint(parsearLSCMD(list_ls_cmd, list_tz))
# print("Parser PS DE CMD")
# pprint.pprint(parsearPSCMD(list_ps_cmd))
# print("Parsear LS de Powershell")
# pprint.pprint(parsearLSPowershell(list_ls_powershell))
# print("Parser PS de Powershell")
# pprint.pprint(parsearPSPowershell(list_ps_powershell))
