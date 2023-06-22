import kryptone
from kryptone.management.base import ProjectCommand
from kryptone.registry import registry


class Command(ProjectCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-n',
            '--name', 
            help='Spider name to execute', 
            type=str
        )
        parser.add_argument(
            '-w',
            '--wait-time', 
            help='The amount of time the crawler should wait before going to the next pages',
            type=int
        )

    def execute(self, namespace):
        kryptone.setup()

        if not registry.spiders_ready:
            raise ValueError(('The spiders for the current project '
                              'were not properly configured'))
        
        from kryptone.conf import settings

        wait_time = namespace.wait_time or settings.WAIT_TIME

        if namespace.name is not None:
            spider_config = registry.get_spider(namespace.name)
            if not spider_config.is_automater:
                raise ValueError(f'{spider_config} is not an automater')
            spider_config.run(wait_time=wait_time)
        else:
            registry.run_all_automaters(wait_time=wait_time)
