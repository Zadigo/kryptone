import unittest
from kryptone.db.backends import BaseRow

from kryptone.db.fields import CharField
from kryptone.db.tables import Table


class TestTable(unittest.TestCase):
    def setUp(self):
        self.table = Table('my_table', fields=[
            CharField('name')
        ])

    def test_fields_map(self):
        self.assertIn('id', self.table.fields_map)
        self.assertIsInstance(self.table.fields_map, dict)
        self.assertTrue(self.table.has_field('id'))

    def test_build_field_parameters(self):
        parameters = self.table.build_field_parameters()
        self.assertListEqual(
            parameters,
            [
                ['name', 'text', 'not null'],
                ['id', 'integer', 'primary key', 'autoincrement', 'not null']
            ]
        )

    def test_prepare_table(self):
        # 1. Build the field paraters
        # 2. Create the table in SQlite
        self.table.prepare()
        self.table.create(name='Kendall Jenner')
        result = self.table.filter(name__contains='Kendall')
        self.assertEqual(result[0].name, 'Kendall Jenner')

        # Test queries
        row = self.table.first()
        self.assertIsInstance(row, BaseRow)

        row = self.table.last()
        self.assertIsInstance(row, BaseRow)


if __name__ == '__main__':
    unittest.main()
