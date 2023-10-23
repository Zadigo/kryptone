import pathlib
import unittest

from kryptone.conf import settings
from kryptone.db.backends import Field, Table

settings['PROJECT_PATH'] = pathlib.Path(__file__).parent.parent.absolute().joinpath('testproject')


class TestField(unittest.TestCase):
    def test_field_params(self):
        field = Field('name')
        Table('celebrities', 'hollywood', fields=[field])

        result = field.field_parameters()
        self.assertListEqual(result, ['name', 'text', 'not null'])

        field.null = True
        field.default = 'Kendall'
        result = field.field_parameters()
        self.assertListEqual(
            result,
            # FIXME: There is two times name
            ['name', 'name', 'text', 'null', 'default', "'Kendall'"]
        )

        field.unique = True
        result = field.field_parameters()
        self.assertListEqual(
            result,
            # FIXME: There is two times name
            ['name', 'name', 'text', 'null', 'default', "'Kendall'"]
        )

    def test_to_database(self):
        field = Field('name')
        result = field.to_database('Kendall')
        self.assertEqual(result, 'Kendall')

if __name__ == '__main__':
    unittest.main()
