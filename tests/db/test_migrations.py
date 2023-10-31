import pathlib
import unittest

from kryptone.db.backends import Migrations
from kryptone.conf import settings
from kryptone.db.backends import Table
from kryptone.db.backends import Field


settings['PROJECT_PATH'] = pathlib.Path(__file__).parent.parent.absolute().joinpath('testproject')


TEST_MIGRATION = {
    "id": "fe81zef5",
    "date": None,
    "number": 1,
    "tables": [
        {
            "name": "urls_seen",
            "fields": [
                {
                    "name": "id",
                    "verbose_name": "id",
                    "params": [
                        "integer",
                        "primary key"
                    ]
                },
                {
                    "name": "url",
                    "verbose_name": None,
                    "params": [
                        "text",
                        "null"
                    ]
                },
                {
                    "name": "date",
                    "verbose_name": None,
                    "params": [
                        "text",
                        "not null"
                    ]
                }
            ],
            "indexes": [
                "url"
            ]
        }
    ]
}


# table = Table('movies', 'celebrities', )

class TestMigrations(unittest.TestCase):
    def setUp(self) -> None:
        self.instance = Migrations()

    def test_table_map(self):
        self.assertListEqual(self.instance.table_map, ['urls_seen'])
        self.assertIn('urls_seen', self.instance.table_map)

    def test_field_construction(self):
        result = self.instance.construct_fields('urls_seen')
        self.assertIsInstance(result, list)
        self.assertListEqual(result[1], ['url', None, ['text', 'null']])
        self.assertTrue(result[1][0], 'url')

    def test_get_table_fields(self):
        result = self.instance.get_table_fields('urls_seen')
        self.assertIsInstance(result[0], dict)
        self.assertIn('name', result[0])

    def test_fields_reconstruction(self):
        result = self.instance.reconstruct_table_fields(table_name='urls_seen')
        field_id = result[0]
        field_url = result[1]
        self.assertIsInstance(field_url, Field)
        self.assertTrue(field_url.name == 'url')
        # self.assertListEqual(
        #     self.instance.get_table_fields('urls_seen')[1]['params'], 
        #     field_url.base_field_parameters
        # )
        self.assertTrue(field_id.primary_key)
        print(vars(field_id))

if __name__ == '__main__':
    unittest.main()
