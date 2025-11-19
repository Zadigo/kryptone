from kryptone.management.base import BaseCommand
import unittest


class TestBaseCommand(unittest.TestCase):
    def test_create_parser(self):
        command = BaseCommand()
        parser = command.create_parser()
        self.assertIsNotNone(parser)
        self.assertIn('command', parser._actions[1].dest)

    def test_add_arguments_not_implemented(self):
        command = BaseCommand()
        parser = command.create_parser()
        result = command.add_arguments(parser)
        self.assertEqual(result, NotImplemented)

    def test_execute_not_implemented(self):
        command = BaseCommand()
        result = command.execute()
        self.assertEqual(result, NotImplemented)
