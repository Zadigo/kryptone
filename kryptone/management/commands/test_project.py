import kryptone
from kryptone.management.base import ProjectCommand
from kryptone.registry import registry


class Command(ProjectCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--settings',
            help='A settings module to use e.g. myproject.settings',
            action='store_true'
        )

    def execute(self, namespace):
        kryptone.setup()

        if not registry.spiders_ready:
            raise ValueError(('The spiders for the current project '
                              'were not properly configured'))
