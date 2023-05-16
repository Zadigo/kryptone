import logging
import pathlib
from collections import defaultdict

PROJECT_PATH = pathlib.Path('.').absolute()


class Logger:
    instance = None

    def __init__(self, name='MAIN'):
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        logger.addHandler(handler)

        log_format = logging.Formatter(
            '%(asctime)s %(name)s: %(message)s',
            datefmt='%Y-%m-%d'
        )
        handler.setFormatter(log_format)
        self.instance = logger


logger = Logger()


# class Cache:
#     configuration = None
#     container = defaultdict(list)

#     def __init__(self):
#         logger.instance.info('Cache loaded')

#     def __str__(self):
#         return str(self.container)

#     def __len__(self):
#         keys = self.container.keys()
#         return sum([self.container[x] for x in keys])

#     def __getitem__(self, key):
#         return self.container[key]

#     def set_value(self, key, value):
#         if isinstance(value, list):
#             self.container[key].extend(value)
#         else:
#             self.container[key].append(value)

#     def get_value(self, key):
#         return self.container[key]

#     def reset_key(self, key):
#         self.container[key] = []

#     # def persist(self, key):
#     #     """Persist the data of a given key
#     #     to the "cache.csv" file"""
#     #     file_path = PROJECT_PATH / 'neptunia/data/cache.csv'
#     #     with open(file_path, mode='w', newline='', encoding='utf-8') as f:
#     #         csv_writer = csv.writer(f)
#     #         map_to_csv = map(lambda x: [x], self.get(key))
#     #         csv_writer.writerows(map_to_csv)


# cache = Cache()
