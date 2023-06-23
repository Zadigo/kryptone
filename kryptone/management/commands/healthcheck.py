from kryptone.management.base import ProjectCommand
from kryptone.registry import registry


class Command(ProjectCommand):
    def execute(self, namespace):
        print(registry.has_running_spiders)
