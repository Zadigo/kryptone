import multiprocessing

import kryptone
from kryptone.checks.core import checks_registry
# from kryptone.core.process import BaseProcess
from kryptone.core.server.app import application
from kryptone.management.base import ProjectCommand
from kryptone.registry import registry
from kryptone.db.backends import Table


class Command(ProjectCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'name',
            help='Spider name to execute',
            type=str
        )
        parser.add_argument(
            '-l',
            '--language',
            help='Specify the website language',
            default='fr',
            type=str
        )
        parser.add_argument(
            '-u',
            '--start-urls',
            default=[],
            help='A list of starting urls to use',
            action='append'
        )

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()

        if not registry.spiders_ready:
            raise ValueError((
                "The spiders for the current project "
                "were not properly configured"
            ))

        params = {
            'start_urls': namespace.start_urls,
            'language': namespace.language
        }

        spider_config = registry.get_spider(namespace.name)
        reactor = application(registry, spider_config)
