import pandas

import kryptone
from kryptone import logger
from kryptone.checks.core import checks_registry
from kryptone.conf import settings
from kryptone.management.base import ProjectCommand
from kryptone.utils.file_readers import read_json_document
from kryptone.utils.urls import URLIgnoreTest


class Command(ProjectCommand):
    requires_system_checks = True

    def add_arguments(self, parser):
        parser.add_argument(
            'paths',
            nargs='+',
            help='Paths to ignore and test'
        )

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()

        data = read_json_document('cache.json')
        urls_to_visit = data['urls_to_visit']

        df = pandas.DataFrame({'urls': urls_to_visit})
        instance = URLIgnoreTest('test_urls', paths=namespace.paths)

        def test_result(url):
            return instance(url)

        df['ignore_url'] = df['urls'].map(test_result)
        ignored_urls = df[df['ignore_url'] == True]
        ignored_urls['urls'].to_csv(
            settings.PROJECT_PATH / 'tested_urls.csv',
            index=False
        )
        ignored_urls = ignored_urls.sort_values('urls')
        logger.info(
            "Url extraction complete. "
            f"{ignored_urls['ignore_url'].count()} extracted urls"
        )
