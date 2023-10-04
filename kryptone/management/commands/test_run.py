import os

import kryptone
from kryptone.checks.core import checks_registry
from kryptone.management.base import ProjectCommand
from kryptone.registry import logger, registry


class Command(ProjectCommand):
    def add_arguments(self, parser):
        pass

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
        # if namespace.name is not None:
        #     spider_config = registry.get_spider(namespace.name)
        #     spider_config.run(**params)
        # else:
        registry.run_all_spiders(**params)
        logger.info('Test run completed')
