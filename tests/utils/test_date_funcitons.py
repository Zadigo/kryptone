import datetime
from unittest import TestCase

from kryptone.utils.date_functions import get_current_date, is_expired


class TestDataFunctions(TestCase):
    def test_get_current_date(self):
        result = get_current_date()
        print(result)
        self.assertIsInstance(result, datetime.datetime)

    def test_is_expired(self):
        d = get_current_date()
        result = is_expired(d)
