from django.core import management
from django.core.management.commands import loaddata

def run():
    management.call_command('flush', verbosity=1, interactive=False)
    management.call_command('makemigrations', 'backendapi')
    management.call_command('migrate')
    management.call_command('loaddata', 'data.json', verbosity=1)
    management.call_command('runscript', 'load_modules', verbosity=1)
    # management.call_command('loaddata', 'mock.json', verbosity=1)
    # management.call_command(loaddata.Command(), 'test_data', verbosity=0)
