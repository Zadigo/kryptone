from collections import defaultdict


class Cache:
    """A simple cache storage
    for storing data during the
    execution of the web scrapper"""

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

    def extend_list(self, key, values):
        # TEST: This has to be tested
        items = self.container[key]
        items.extend(values)

    def set_value_and_backup(self, key, value, extend=False, filename=None):
        # TEST: This has to be tested
        from kryptone.utils.file_readers import write_json_document
        container = self.container[key]
        if extend:
            container.extend(value)
        else:
            container.append(value)
        write_json_document(filename, container) 
