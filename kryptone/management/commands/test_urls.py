import pandas

import kryptone
from kryptone import logger
from kryptone.checks.core import checks_registry
from kryptone.management.base import ProjectCommand
from kryptone.utils.file_readers import read_json_document, write_json_document
from kryptone.utils.urls import URLIgnoreRegexTest, URLIgnoreTest


class Command(ProjectCommand):
    requires_system_checks = True

    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            '--paths',
            help='Paths to ignore and test'
        )

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()

        data = read_json_document('cache.json')
        urls_to_visit = data['urls_to_visit']

        instance = URLIgnoreTest()
        # visited_urls = data['visited_urls']

        # df = pandas.DataFrame({'urls': urls_to_visit})
        # df['is_invalid'] = df['urls'].map(lambda x: namespace.pattern in x)

        # valid_urls = df[df['is_invalid'] == False]
        # invalid_urls = df[df['is_invalid'] == True]

        # valid_urls_list = valid_urls['urls'].values.tolist()
        # invalid_urls_list = invalid_urls['urls'].values.tolist()

        # data['urls_to_visit'] = valid_urls_list
        # visited_urls.extend(invalid_urls_list)
        # data['visited_urls'] = visited_urls

        # if valid_urls_list or invalid_urls_list:
        #     write_json_document('cache.json', data)
        # logger.info('The cache file was successfully filtered')
