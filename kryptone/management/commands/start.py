import kryptone
from kryptone.management.base import ProjectCommand
from kryptone.registry import registry


class Command(ProjectCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-a',
            '--run-audit', 
            help='Audit the website',
            type=bool,
            default=False
        )
        parser.add_argument(
            '-c',
            '--crawl', 
            help='Whether the robot should crawl the whole website',
            type=bool,
            default=True
        )
        parser.add_argument(
            '-d',
            '--debug-mode', 
            help='Run the crawler in debug mode',
            default=False,
            type=bool
        )
        parser.add_argument(
            '-l',
            '--language', 
            help='Specify the website language',
            default='fr',
            type=str
        )
        parser.add_argument(
            '-n',
            '--name', 
            help='Spider name to execute', 
            type=str
        )
        parser.add_argument(
            '-u',
            '--start-urls', 
            help='A list of starting urls to use',
            action='append'
        )
        parser.add_argument(
            '-w',
            '--wait-time', 
            help='The amount of time the crawler should wait before going to the next pages',
            default=25,
            type=int
        )

    def execute(self, namespace):
        kryptone.setup()

        if not registry.spiders_ready:
            raise ValueError(('The spiders for the current project '
                              'were not properly configured'))

        # TODO: Check if the config is an automation
        # class or not 
        if namespace.name is not None:
            spider_config = registry.get_spider(namespace.name)
            spider_config.run(
                start_urls=namespace.start_urls,
                debug_mode=namespace.debug_mode,
                wait_time=namespace.wait_time,
                run_audit=namespace.run_audit,
                language=namespace.language,
                crawl=namespace.crawl
            )
        else:
            registry.run_all_spiders(
                start_urls=namespace.start_urls,
                debug_mode=namespace.debug_mode,
                wait_time=namespace.wait_time,
                run_audit=namespace.run_audit,
                language=namespace.language,
                crawl=namespace.crawl
            )
