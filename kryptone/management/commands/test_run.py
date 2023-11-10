import os

import kryptone
from kryptone.checks.core import checks_registry
from kryptone.management.base import ProjectCommand
from kryptone.registry import registry


class Command(ProjectCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'name',
            help='Spider name to execute',
            type=str
        )

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()

        if not registry.spiders_ready:
            raise ValueError((
                "The spiders for the current project "
                "were not properly configured"
            ))

        params = {}

        os.environ.setdefault('KYRPTONE_TEST_RUN', 'True')
        spider_config = registry.get_spider(namespace.name)
        spider_config.run(**params)
