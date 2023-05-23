import subprocess
from kryptone import settings

app_path = settings.PROJECT_PATH / 'kryptone/app.py'
arguments = ['python', app_path]
subprocess.call(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
