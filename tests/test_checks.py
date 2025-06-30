import pathlib
import unittest

from kryptone.checks.core import ApplicationChecks, checks_registry
from kryptone.conf import settings

# from django.test import override_settings, modify_settings


class TestApplicationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instance = ApplicationChecks()
        settings['PROJECT_PATH'] = pathlib.Path(
            './tests/testproject'
        ).absolute()
        print(pathlib.Path('./testproject').absolute())
        cls.settings = settings

    def test_register_check(self):
        @self.instance.register()
        def custom_check():
            return []

        self.assertIn('custom_check', self.instance._checks)

        # When we call run, we should not get
        # any errors since custom_check is successful
        self.instance.run()
        self.assertListEqual(self.instance._errors, [])

        @self.instance.register()
        def error_custom_check():
            return ['This is a custom error']

        self.assertRaises(Exception, self.instance.run)


class TestChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = './tests/testproject'
        settings['PROJECT_PATH'] = pathlib.Path(path).absolute()
        cls.settings = settings

        # Import the checks in order to force
        # the class to be populated
        # from kryptone.checks import project
        from kryptone.checks.core import checks_registry
        cls.registry = checks_registry

    def test_global_class(self):
        keys = checks_registry._checks.keys()
        self.assertTrue(len(keys) > 0)

    # def test_check_webdriver(self):
    #     func = self.registry._checks['webdriver_name']
    #     result = func()
    #     self.assertListEqual(result, [])

    #     # Expect an array with with error if we implement
    #     # something that this not expected in the settings
    #     self.settings['WEBRIVER'] = 'Firefox'
    #     result = func()
    #     self.assertNotEqual(result, [], msg='List is empty')
