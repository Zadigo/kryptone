from typing import Literal

from kryptone.management.base import ProjectCommand

class Command(ProjectCommand):
    requires_system_checks: Literal[True] = ...
