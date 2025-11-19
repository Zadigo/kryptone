from argparse import ArgumentParser, Namespace
from collections import OrderedDict
from typing import Optional


class BaseCommand:
    """
    Represents a base Kryptone command. Each command
    class to subclass this in order to be registered
    """

    help_text = ''
    command_registry = OrderedDict()
    requires_system_checks = False

    def create_parser(self, **kwargs):
        parser = ArgumentParser(
            description=self.help_text or None,
            **kwargs
        )
        # These are the base arguments that are implemented
        # to the base parser and then passed in the add_arguments
        # of the subclasses for additional arguments to be added
        parser.add_argument('command', help='Command to use', type=str)

        # Adds other optional arguments to the parser
        # by the Command subclasses
        self.add_arguments(parser)
        return parser

    def add_arguments(self, parser: ArgumentParser):
        """
        Adds additional arguments in addition with
        the ones that were already implemented above. Each
        subclass can implement additional arguments
        """
        return NotImplemented

    def execute(self, namespace: Optional[Namespace] = None):
        """
        Represents the main logic behind an argument passed
        using the command line. Each Command should override
        this definition to implement their custom logic so that
        when this is called, the logic is run
        """
        return NotImplemented


class ProjectCommand(BaseCommand):
    requires_system_checks = True
