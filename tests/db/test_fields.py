import unittest

from kryptone.db.fields import BooleanField, Field, IntegerField
from kryptone.db.tables import Table


class TestField(unittest.TestCase):
    def test_field_params(self):
        field = Field('name')
        field.table = Table('celebrities')

        result = field.field_parameters()
        self.assertListEqual(result, ['name', 'text', 'not null'])

        field.null = True
        field.default = 'Kendall'
        result = field.field_parameters()
        self.assertListEqual(
            result,
            # FIXME: There is two times name
            ['name', 'text', 'default', "'Kendall'", 'null']
        )

        field.unique = True
        result = field.field_parameters()
        self.assertListEqual(
            result,
            # FIXME: There is two times name
            ['name', 'text', 'default', "'Kendall'", 'null', 'unique']
        )

    def test_to_database(self):
        field = Field('name')
        result = field.to_database('Kendall')
        self.assertEqual(result, 'Kendall')


class TestIntegerField(unittest.TestCase):
    def test_result(self):
        field = IntegerField('age')
        result = field.to_database(1)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 1)


class TestBooleanField(unittest.TestCase):
    def test_result(self):
        field = BooleanField('completed')

        result = field.to_database(0)
        self.assertEqual(result, 0)

        result = field.to_database(True)
        self.assertEqual(result, 1)

        result = field.to_database('true')
        self.assertEqual(result, 1)


if __name__ == '__main__':
    unittest.main()
