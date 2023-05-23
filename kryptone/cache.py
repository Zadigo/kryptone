from collections import defaultdict


class Cache:
    """A simple cache storage
    for the web scrapper"""
    configuration = None
    container = defaultdict(list)

    def __init__(self):
        from kryptone import logger
        logger.info('Cache loaded')

    def __str__(self):
        return str(self.container)

    def __len__(self):
        keys = self.container.keys()
        return sum([self.container[x] for x in keys])

    def __getitem__(self, key):
        return self.container[key]

    def set_value(self, key, value):
        if isinstance(value, list):
            self.container[key].extend(value)
        else:
            self.container[key].append(value)

    def get_value(self, key):
        return self.container[key]

    def reset_key(self, key):
        self.container[key] = []
