import unittest

from kryptone.db.backends import BaseRow
from kryptone.db.queries import Query
from tests.db import create_table


class TestQuery(unittest.TestCase):
    def setUp(self):        
        backend = create_table()
        select_clause = backend.SELECT.format_map({
            'fields': backend.comma_join(['rowid', '*']),
            'table': backend.quote_value('celebrities')
        })
        self.instance = Query(backend, [select_clause])

    def test_run(self):
        self.instance.run()
        first_row = self.instance.result_cache[0]
        self.assertIsInstance(first_row, BaseRow)
        self.assertIn('Kendall Jenner', first_row)


if __name__ == '__main__':
    unittest.main()
