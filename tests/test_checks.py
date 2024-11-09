import unittest

from kryptone.checks.core import checks_registry
from kryptone.conf import settings


class TestChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings['PROJECT_PATH'] = settings.GLOBAL_KRYPTONE_PATH.parent.joinpath(
            'tests',
            'testproject'
        )

    def test_global_class(self):
        keys = checks_registry._checks.keys()
        self.assertTrue(len(keys) > 0)

    def test_on_basic_settings(self):
        checks_registry.run()
