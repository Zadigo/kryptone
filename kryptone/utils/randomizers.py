import random
from typing import Callable

from internal_types import TypePath
from kryptone.conf import settings
from kryptone.utils.file_readers import read_document
from functools import wraps


def random_user_agent(func: Callable[[TypePath], str]) -> Callable[[], str]:
    @wraps(func)
    def wrapper():
        path = settings.GLOBAL_KRYPTONE_PATH / 'data/user_agents.txt'
        data = func(path)

        user_agents = data.split('\n')
        return random.choice(user_agents)
    return wrapper


RANDOM_USER_AGENT = random_user_agent(read_document)
