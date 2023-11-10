import kryptone
from kryptone.management.base import ProjectCommand
from kryptone.registry import registry
from kryptone.core.server import run_server


class Command(ProjectCommand):
    requires_system_checks = True
    
    def add_arguments(self, parser):
        pass
    
    def execute(self, namespace):
        run_server()
