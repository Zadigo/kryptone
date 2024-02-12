import kryptone
from kryptone.checks.core import checks_registry
from kryptone.management.base import ProjectCommand
from kryptone.registry import registry


class Command(ProjectCommand):
    requires_system_checks = True

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
        parser.add_argument(
            '-w',
            '--windows',
            type=int,
            default=0,
            help='Number of windows to launch for a spider'
        )

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()

        if not registry.spiders_ready:
            raise ValueError((
                "The spiders for the current project "
                "were not properly configured"
            ))

        # params = {
        #     'start_urls': namespace.start_urls,
        #     'language': namespace.language
        # }
        # spider_config = registry.get_spider(namespace.name)
        # spider_config.run(**params)

        params = {
            'start_urls': namespace.start_urls,
            'language': namespace.language
        }

        spider_config = registry.get_spider(namespace.name)
        if namespace.windows < 0 or namespace.windows > 8:
            raise ValueError('Number of windows should be between 1 and 8')

        spider_config.run(
            windows=namespace.windows,
            **params
        )

        # TODO: Try and execute multiple instances of selenium at once
        # if namespace.instances < 0 or namespace.instances > 3:
        #     raise ValueError('Number of instances should be between 1 and 3')

        # params = {
        #     'start_urls': namespace.start_urls,
        #     'language': namespace.language
        # }
        # spider_config = registry.get_spider(namespace.name)

        # if namespace.instances > 1:
        #     async def main():
        #         tasks, instances = await spider_config.multi_run(
        #             number_of_instances=namespace.instances,
        #         )

        #         for coroutine in asyncio.as_completed(tasks):
        #             await coroutine
        #         # await asyncio.gather(*tasks)

        #     asyncio.run(main())
        # else:
        #     spider_config.run(**params)
