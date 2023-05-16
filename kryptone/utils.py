import json
import random


def read_document(filename):
    with open(filename, mode='r', encoding='utf-8') as f:
        data = f.read()
    return data


def write_json_document(filename, data):
    with open(filename, mode='w+', encoding='utf-8') as f:
        # data = {'urls_to_visit': [], 'visited_urls': ['http://example.com']}
        json.dump(data, f, indent=4)


def read_json_document(filename):
    with open(filename, mode='r', encoding='utf-8') as f:
        data = json.load(f)
        return data


def random_user_agent(func):
    def wrapper():
        data = func('data/user_agents.txt')
        return random.choice(data)
    return wrapper


RANDOM_USER_AGENT = random_user_agent(read_json_document)


def drop_null(items):
    for item in items:
        if item is not None:
            yield item
