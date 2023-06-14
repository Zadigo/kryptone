import subprocess
from kryptone.conf import settings

app_path = 'tests/testproject/manage.py'
arguments = ['python', app_path, 'start', '-d True', '-c False']
subprocess.call(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
