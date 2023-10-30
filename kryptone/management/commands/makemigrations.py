import kryptone
from kryptone.management.base import ProjectCommand
from kryptone.checks.core import checks_registry
from kryptone.contrib.database import database


class Command(ProjectCommand):
    requires_system_checks = True

    def execute(self, namespace):
        kryptone.setup()
        checks_registry.run()
        database.make_migrations()
