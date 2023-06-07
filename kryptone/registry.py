import os
from importlib import import_module
from pathlib import Path

from kryptone.signals import Signal

registry_populated = Signal()

ENVIRONMENT_VARIABLE = 'KRYPTONE_SPIDER'


class MasterRegistry:
    @property
    def spiders_ready(self):
        return True

    def populate(self):
        dotted_path = os.environ.get(ENVIRONMENT_VARIABLE, None)

        if dotted_path is None:
            # The user is lauching the application outside
            # of a project (standalone), it's
            # his responsibility to provide a module where
            # the spiders are located. This is done in order
            # to not completly block the project from functionning
            raise ValueError('Requires project')

        try:
            project_module = import_module(dotted_path)
        except ImportError:
            raise ImportError(
                f"Could not load the project's related module: '{dotted_path}'")

        from kryptone import settings

        self.absolute_path = Path(project_module.__path__[0])
        self.project_name = self.absolute_path.name
        setattr(settings, 'PROJECT_PATH', self.absolute_path)

        registry_populated.send(self, registry=registry)

    def get_spider(self, name):
        pass


registry = MasterRegistry()
