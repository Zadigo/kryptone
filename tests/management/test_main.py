import inspect
import unittest

from kryptone.management import (Utility, collect_commands,
                                 execute_command_inline)
from kryptone.management.base import BaseCommand


class HelpCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show verbose help information'
        )

    def execute(self, namespace=None):
        pass


class TestUtility(unittest.TestCase):
    def setUp(self):
        self.utility = Utility()
        self.utility.commands_registry['help'] = HelpCommand()

    @unittest.skip('The namespace is the one of test itself and creates an error')
    def test_call_command(self):
        incoming_command = ['manage.py', 'help']
        command_instance = self.utility.call_command(incoming_command)


class TestCollectCommands(unittest.TestCase):
    def test_collect_commands(self):
        # Test that collect_commands returns a non-empty list
        commands = collect_commands()
        self.assertIsNotNone(commands)

        commands = list(commands)
        self.assertGreater(len(commands), 0)

        for item in commands:
            # Item is the full path to the command module
            with self.subTest(item=item):
                self.assertIsInstance(item, str)


class TestExecuteCommandInline(unittest.TestCase):
    def test_execute_command_inline_no_args(self):
        # Test with no arguments
        result = execute_command_inline(['manage.py'])
        self.assertIsNone(result)

    def test_execute_command_inline_invalid_command(self):
        # Test with an invalid command
        with self.assertRaises(ValueError) as context:
            execute_command_inline(['manage.py', 'invalid_command'])
        self.assertIn("Command 'invalid_command' does not exist",
                      str(context.exception))
