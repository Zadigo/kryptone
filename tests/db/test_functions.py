import unittest
from kryptone.db.backends import SQLiteBackend

from kryptone.db.functions import Max
from tests.db import create_table

class TestFunctions(unittest.TestCase):
    def test_max_function(self):
        table = create_table()
        instance = Max('age')
        instance.backend = table.backend
        sql = instance.function_sql()
        expected_sql = "select rowid, * from celebrities where age=(select max(age) from celebrities)"
        self.assertTrue(sql == expected_sql)


if __name__ == '__main__':
    unittest.main()
