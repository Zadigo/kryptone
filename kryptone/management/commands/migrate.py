import kryptone
from kryptone.checks.core import checks_registry
from kryptone.conf import settings
from kryptone.contrib.database import get_database
from kryptone.management.base import ProjectCommand


class Command(ProjectCommand):
    requires_system_checks = True

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()
        database = get_database()
        database.make_migrations()
