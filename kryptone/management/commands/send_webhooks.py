import kryptone
from kryptone import logger
from kryptone.management.base import ProjectCommand
from kryptone.checks.core import checks_registry
import pandas
import asyncio
from kryptone.conf import settings
from kryptone.utils.file_readers import read_json_document
from kryptone.webhooks import Webhooks


class Command(ProjectCommand):
    requires_system_checks = True

    def add_arguments(self, parser):
        pass

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()

        data = read_json_document('products.json')
        instance = Webhooks(settings.STORAGE_BACKENDS['webhooks'])
        asyncio.run(instance.resolve(data))
