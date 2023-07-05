import subprocess
import threading
import time

from kryptone import logger
from kryptone.db.connections import redis_connection
from kryptone.signals import Signal

server_started = Signal()


class BaseServer:
    def __init__(self):
        logger.info('Starting server...')
        server_started.send(self)

    def run(self, *args, **kwargs):
        pass


class TaskServer(BaseServer):
    def __init__(self):
        super().__init__()
        self.connection = redis_connection()

    @property
    def has_tasks(self):
        """Checks the Redis backend to see
        if there are tasks that need to
        be executed"""
        return len(self.tasks) > 0

    @property
    def tasks(self):
        try:
            return self.connection.get('kryptone_tasks')
        except:
            return []

    def run(self, *args, **kwargs):
        if self.has_tasks:
            print(self.tasks)
        time.sleep(3)


def run_server(*args, **kwargs):
    """Starts the server for Kryptone. This
    will essentially poll the database backend
    for a trigger to launch the web scrapper"""
    server = TaskServer()
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


run_server()
