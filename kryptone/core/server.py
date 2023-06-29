import subprocess
import threading
import time
from functools import lru_cache
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
        return len(self.tasks()) > 0

    @lru_cache(maxsize=100)
    def tasks(self):
        # Scan the redis database for all
        # available tasks
        _, keys = self.connection.scan()
        filtered_tasks = filter(
            lambda task_name: task_name.decode('utf-8').startswith('task_'),
            keys
        )
        return list(filtered_tasks)

    def tasks_to_execute(self):
        tasks = []
        for task_name in self.tasks():
            state = self.connection.hget(task_name, 'completed')
            if not state:
                continue
            tasks.append(task_name)

    # def execute_tasks(self):
    #     threads = []
    #     for task_name in self.tasks_to_execute():
    #         threads.append(
    #             threading.Thread(
    #                 target=None,
    #                 name=task_name
    #             )
    #         )

    def run(self, *args, **kwargs):
        if self.has_tasks:
            # subprocess.call()
            logger.info(self.tasks())
        time.sleep(3)
        print('google')


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
