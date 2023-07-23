import multiprocessing

import kryptone
from kryptone.checks.core import checks_registry
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
            default=[],
            help='A list of starting urls to use',
            action='append'
        )
        # parser.add_argument(
        #     '-w',
        #     '--wait-time', 
        #     help='The amount of time the crawler should wait before going to the next pages',
        #     default=25,
        #     type=int
        # )

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
            'debug_mode': namespace.debug_mode,
            # 'wait_time': namespace.wait_time,
            'run_audit': namespace.run_audit,
            'language': namespace.language
        }

        if namespace.name is not None:
            spider_config = registry.get_spider(namespace.name)
            spider_config.run(**params)
            # process = multiprocessing.Process(
            #     target=spider_config.run,
            #     kwargs=params
            # )
            # try:
            #     process.start()
            # except:
            #     raise
            # else:
            #     process.join()
        else:
            registry.run_all_spiders(**params)
            # process = multiprocessing.Process(
            #     target=registry.run_all_spiders, 
            #     kwargs=params
            # )
            # try:
            #     process.start()
            # except:
            #     raise
            # else:
            #     process.join()
