import unittest
from kryptone.db.backends import SQLiteBackend

from kryptone.db.functions import Lower, Max, Upper, Length, ExtractYear
from tests.db import create_table


class TestFunctions(unittest.TestCase):
    def test_max_function(self):
        table = create_table()
        instance = Max('age')
        instance.backend = table.backend
        sql = instance.function_sql()
        expected_sql = "select rowid, * from celebrities where age=(select max(age) from celebrities)"
        self.assertTrue(sql == expected_sql)

    def test_lower_function(self):
        table = create_table()
        instance = Lower('age')
        instance.backend = table.backend
        sql = instance.function_sql()
        expected_sql = 'lower(age)'
        self.assertEqual(sql, expected_sql)

    def test_upper_function(self):
        table = create_table()
        instance = Upper('age')
        instance.backend = table.backend
        sql = instance.function_sql()
        expected_sql = 'upper(age)'
        self.assertEqual(sql, expected_sql)

    def test_length_function(self):
        table = create_table()
        instance = Length('age')
        instance.backend = table.backend
        sql = instance.function_sql()
        expected_sql = 'length(age)'
        self.assertEqual(sql, expected_sql)

    def test_extract_year_function(self):
        table = create_table()
        instance = ExtractYear('date_of_birth')
        instance.backend = table.backend
        sql = instance.function_sql()
        expected_sql = "strftime('%Y', date_of_birth)"
        self.assertEqual(sql, expected_sql)


if __name__ == '__main__':
    unittest.main()
