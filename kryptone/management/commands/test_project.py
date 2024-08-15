import time

import kryptone
from kryptone.checks.core import checks_registry
from kryptone.management.base import ProjectCommand
from kryptone.registry import registry


class Command(ProjectCommand):
    requires_system_checks = True
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--settings',
            help='A settings module to use e.g. myproject.settings',
            action='store_true'
        )

    def execute(self, namespace):
        # This test runs the setup method in 
        # and verifies that it completes
        # without raising any error
        start_time = time.time()
        kryptone.setup()
        checks_registry.run()

        if not registry.spiders_ready:
            message = (
                "The spiders for the current project "
                "were not properly configured"
            )
            raise ValueError(message)
        end_time = round(time.time() - start_time, 1)
        kryptone.logger.info(f'Test completed in {end_time}s')
