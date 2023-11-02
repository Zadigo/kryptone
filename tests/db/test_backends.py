import unittest
from kryptone.db.backends import BaseRow, SQLiteBackend


def create_sqlite_table(backend):
    sql = 'create table if not exists test_table (id primary key, name not null)'
    finalized_sql = backend.finalize_sql(sql)
    backend.connection.execute(finalized_sql)
    backend.connection.commit()
    return backend


class TestSQLiteBackend(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = SQLiteBackend()

    def test_connection(self):
        def test_cursor():
            try:
                self.backend.connection.cursor()
                return True
            except:
                return False
        self.assertTrue(test_cursor())

    def test_list_table_sql(self):
        results = self.backend.list_tables_sql()
        self.assertListEqual(results, [])

        backend = create_sqlite_table(self.backend)
        # finalized_sql = self.backend.finalize_sql(sql)
        # self.backend.connection.execute(finalized_sql)
        # self.backend.connection.commit()
        results = backend.list_tables_sql()
        self.assertTrue(len(results) > 0)
        self.assertIsInstance(results[0], BaseRow)
        self.assertTrue(results[0].name == 'test_table')


if __name__ == '__main__':
    unittest.main()
