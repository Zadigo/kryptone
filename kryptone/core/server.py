import subprocess
import threading

from kryptone import logger
from kryptone.db.connections import redis_connection
from kryptone.signals import Signal

server_started = Signal()

class BaseServer:
    def __init__(self):
        self.trigger = False
        self.connection = redis_connection()
        logger.info('Starting server...')
        server_started.send(self)

    def run(self):
        if self.connection:
            self.trigger = self.connection.get('project')

        if self.trigger:
            cmd = ['python', 'manage.py', 'start']
            subprocess.call(cmd)
            if self.connection:
                self.connection.set('project', False)


def run_server(*args, **kwargs):
    """Starts the server for Kryptone. This
    will essentially poll the database backend
    for a trigger to launch the web scrapper"""
    server = BaseServer()
    kryptone_main_thread = threading.Thread(
        target=server.run,
        args=args,
        kwargs=kwargs,
        name='kryptone_main_thread'
    )
    kryptone_main_thread.daemon = True
    kryptone_main_thread.start()
    while True:
        kryptone_main_thread.join()
