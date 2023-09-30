import datetime
import os
import unittest

from kryptone import setup
from kryptone.conf import settings


class TestSetup(unittest.TestCase):
    def setUp(self):
        from kryptone.registry import ENVIRONMENT_VARIABLE
        os.environ.setdefault(ENVIRONMENT_VARIABLE, 'tests.testproject')

        setup()

    def test_webhook_interval(self):
        self.assertIsInstance(settings.WEBHOOK_INTERVAL, datetime.timedelta)


if __name__ == '__main__':
    unittest.main()
