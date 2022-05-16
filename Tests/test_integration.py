import requests
from urllib.parse import urljoin
import pytest

target = 'http://127.0.0.1:8000'

# Utils 

def save_response(response):
    with open('response_result.html', 'wb') as f:
        f.write(response.content)

def as_curl(request): 
    command = "curl -X {method} -H {headers} -d '{data}' '{uri}'"
    method = request.method
    uri = request.url
    data = request.body
    headers = ['"{0}: {1}"'.format(k, v) for k, v in request.headers.items()]
    headers = " -H ".join(headers)
    return command.format(method=method, headers=headers, data=data, uri=uri)

# Tokens

def test_create_token():
    url = urljoin(target,'api-token-auth/')
    data = {'username':'pucara', 'password': 'zuthaka_project'}
    response = requests.post(url, json=data)
    assert response.status_code == 200
    results = response.json()
    assert results.get('token','').isalnum()

@pytest.fixture
def authentication_headers():
    url = urljoin(target,'api-token-auth/')
    data = {'username':'pucara', 'password': 'zuthaka_project'}
    response = requests.post(url, json=data)
    results = response.json()
    headers = {'Authorization': 'Bearer {}'.format(results['token']),
            'Content-Type': 'application/json' }
    return headers

# C2 

def test_c2_types(authentication_headers):
    url = urljoin(target,'c2/types/')
    response = requests.get(url, headers=authentication_headers)
    assert response.status_code == 200
    results = response.json()
    assert results.get('count') >= 1
    assert len(results.get('results')[0]) == 5

def test_c2_types_slashed(authentication_headers):
    url = urljoin(target,'c2/types/')
    response = requests.get(url, headers=authentication_headers)
    assert response.status_code == 200
    results = response.json()
    assert results.get('count') >= 1
    assert len(results.get('results')[0]) == 5

def test_c2_create(authentication_headers):
    data = {"c2_type":1,"options":[{"name":"option 1","value":"value 1"},{"name":"name 2","value":"value 2"}]}
    url =  urljoin(target,'c2/')
    response = requests.post(url, json=data, headers=authentication_headers)
    assert response.status_code == 201
    assert len(response.json().get('options')) == 2
    options =response.json().get('options')
    assert options[0].get('name') == 'option 1'
    assert response.status_code == 201
    c2_id  =response.json()['id']
    url =  urljoin(target,'c2/{}/'.format(c2_id))
    response = requests.get(url, headers=authentication_headers)
    assert response.status_code == 200

def test_c2_update(authentication_headers):
    data = {"options":[{"name":"url","value":"https://192.168.0.1:31337"},{"name":"password","value":"Sup3r53cr3t"}]}
    url =  urljoin(target,'c2/2/')
    response = requests.put(url, json=data, headers=authentication_headers)
    assert response.status_code == 200
    options = response.json().get('options')
    for option in options:
        if option.get('name') == 'url':
            assert option.get('value') == 'https://192.168.0.1:31337'
        if option.get('name') == 'password':
            assert option.get('value') == 'Sup3r53cr3t'

def test_c2_update_denies_system_values(authentication_headers):
    data = {'c2_type':1}
    url =  urljoin(target,'c2/2/')
    response = requests.put(url, json=data, headers=authentication_headers)
    assert response.status_code == 200
    assert response.json().get('c2_type') != 1

def test_c2_created(authentication_headers):
    url =  urljoin(target,'c2/')
    response = requests.get(url, headers=authentication_headers)
    print(url)
    save_response(response)
    assert response.status_code == 200
    assert len(response.json()['results']) >= 1

# Listeners

def test_listener_types(authentication_headers):
    url = urljoin(target,'listeners/types/')
    response = requests.get(url, headers=authentication_headers)
    assert response.status_code == 200
    results = response.json()
    assert results.get('count') >= 1
    assert results['results'][0]['available_c2s'][0]['c2_id'] == 1
    assert isinstance(results['results'][0].get('name'), str)

def test_listener_created(authentication_headers):
    url =  urljoin(target,'listeners/')
    data = {
            "c2_id": 1,
            "listener_type": 1,
            "options": [
                {
                    "name": "interface",
                    "value": "192.168.0.1"
                },
                {
                    "name": "port",
                    "value": "80"
                },
                {
                    "name": "default_delay",
                    "value": "10"
                }
            ]
        }
    response = requests.post(url, json=data, headers=authentication_headers)
    save_response(response)
    assert response.status_code == 201
    assert len(response.json().get('options')) >= 2

def test_listener_update_denies_system_values(authentication_headers):
    data = {'listener_type':1}
    url =  urljoin(target,'listeners/2/')
    response = requests.put(url, json=data, headers=authentication_headers)
    assert response.status_code == 200
    assert response.json().get('listener_type') != 1

# Launchers

def test_launcher_types(authentication_headers):
    url = urljoin(target,'launchers/types/')
    response = requests.get(url, headers=authentication_headers)
    assert response.status_code == 200
    results = response.json()
    assert results.get('count') >= 1
    assert results['results'][0]['available_listeners']

def test_launcher_create_and_download(authentication_headers):
    data = {"launcher_type":1, "listener_id":1,"options":[{"name":"Dotnet Version","value":"Net40"}]}
    url =  urljoin(target,'launchers/')
    response = requests.post(url, json=data, headers=authentication_headers)
    save_response(response)
    assert response.status_code == 201
    assert len(response.json().get('options')) >= 1
    pk = response.json().get('id')
    url = urljoin(target,'launchers/{}/download/'.format(pk))
    response = requests.get(url, headers=authentication_headers)
    save_response(response)
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/octet-stream'


def test_launcher_create_and_delete(authentication_headers):
    data = {"launcher_type":1, "listener_id":1,"options":[{"name":"Dotnet Version","value":"Net40"}]}
    url =  urljoin(target,'launchers/')
    response = requests.post(url, json=data, headers=authentication_headers)
    save_response(response)
    assert response.status_code == 201
    assert len(response.json().get('options')) >= 1
    _id = str(response.json().get('id')) + '/'
    url =  urljoin(url,_id)
    response = requests.delete(url, headers=authentication_headers)
    assert response.status_code == 204

def test_launcher_update_denies_system_values(authentication_headers):
    data = {'launcher_type':2}
    url =  urljoin(target,'launchers/1/')
    response = requests.put(url, json=data, headers=authentication_headers)
    assert response.status_code == 200
    assert response.json().get('launcher_type') != 2


def test_downlaod_launcher(authentication_headers):
    url = urljoin(target,'launchers/1/download/')
    response = requests.get(url, headers=authentication_headers)
    save_response(response)
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/octet-stream'


def test_agents_tasks_events(authentication_headers):
    url =  urljoin(target,'tasks/')
    response = requests.get(url, headers=authentication_headers)
    save_response(response)
    assert response.status_code == 200
    assert len(response.json()['results']) >= 1

