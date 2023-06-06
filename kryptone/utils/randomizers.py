import random

from kryptone import settings
from kryptone.utils.file_readers import read_document


def random_user_agent(func):
    def wrapper():
        data = func(settings.GLOBAL_KRYPTONE_PATH / 'data/user_agents.txt')
        user_agents = data.split('\n')
        return random.choice(user_agents)
    return wrapper


RANDOM_USER_AGENT = random_user_agent(read_document)
