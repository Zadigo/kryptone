import datetime
import secrets
from argparse import ArgumentParser
from kryptone import logger
from kryptone.core.server import run_server
from kryptone.db.connections import redis_connection
from kryptone.management.base import ProjectCommand
from kryptone.registry import registry


class Command(ProjectCommand):
    def execute(self, namespace):
        connection = redis_connection()
        secret_key = secrets.token_hex(15)
        task_name = f'task_{secret_key}'
        task = {
            'id': secret_key,
            'url': None,
            'project_name': None,
            'completed': False,
            'paused': False,
            'creation_date': str(datetime.datetime.now())
        }
        connection.hset(task_name, task)
        logger.info(f'Created task {task_name}')
