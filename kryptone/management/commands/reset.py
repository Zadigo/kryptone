import kryptone
from kryptone import logger
from kryptone.management.base import ProjectCommand
from kryptone.checks.core import checks_registry
from kryptone.conf import settings
from kryptone.utils.file_readers import write_json_document, write_csv_document, write_text_document


class Command(ProjectCommand):
    requires_system_checks = True

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()

        write_json_document('products.json', [])
        write_json_document('performance.json', {})
        write_json_document('cache.json', {})
        write_csv_document('seen_urls.csv', [])
        write_text_document('access.log', '')
        logger.info('Project reset successfully')
