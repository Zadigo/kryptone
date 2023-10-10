from kryptone.management.base import ProjectCommand
from kryptone.registry import registry
from kryptone.core.server.app import application


class Command(ProjectCommand):
    def add_arguments(self, parser):
        pass
    
    def execute(self, namespace):
        reactor = application(registry)
