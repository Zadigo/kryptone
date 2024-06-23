import pathlib
from typing import Literal

from kryptone.management.base import ProjectCommand


class Command(ProjectCommand):
    requires_system_checks: Literal[True] = ...

    def normalize_file_name(self, path: pathlib.Path) -> str: ...
    def create_new_file(
        self, 
        source: str, 
        destination: str,
        project_name: str = ...
    ) -> None: ...
