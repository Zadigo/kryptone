import unittest
from kryptone.db.backends import SQL


class TestSQL(unittest.TestCase):
    def setUp(self):
        self.instance = SQL()

    def test_quote_value(self):
        values = ['name', 'surname', 'key intelligence']
        for value in values:
            with self.subTest(value=value):
                result = self.instance.quote_value(value)
                self.assertTrue(result.startswith("'"))
                self.assertTrue(result.endswith("'"))

        self.assertTrue(isinstance(self.instance.quote_value(1), int))

    def test_comma_join(self):
        values = ['a', 'b', 'c']
        self.assertTrue(self.instance.comma_join(values) == 'a, b, c')

    def test_simple_join(self):
        values = ['a', 'b', 'c']
        self.assertTrue(self.instance.simple_join(values) == 'a b c')

    def test_finalize_sql(self):
        self.assertTrue(self.instance.finalize_sql('a').endswith(';'))
    
    def test_de_sqlize_statement(self):
        self.assertTrue(not self.instance.de_sqlize_statement('a;').endswith(';'))
    
    def test_quote_wildcard(self):
        self.assertTrue(self.instance.quote_startswith('name') == "'name%'")
        self.assertTrue(self.instance.quote_endswith('name') == "'%name'")
        self.assertTrue(self.instance.quote_like('name') == "'%name%'")

    def test_dict_to_sql(self):
        conditions = [
            # expected: (['name__eq'], ["'Kendall'"])
            {'name__eq': 'Kendall'}
        ]
        for condition in conditions:
            with self.subTest(condition=condition):
                result = self.instance.dict_to_sql(condition)
                self.assertIsInstance(result, tuple)
                self.assertListEqual(result[0], ['name__eq'])
                self.assertTrue(result[1][0].startswith("'"))

    # def test_complex_dict_to_sql(self):
    #     test_value = {'url__gt': 'Kendall'}
    #     result = self.instance.complex_dict_to_sql(test_value)
    #     self.assertListEqual(result, [['url', '>', "'Kendall'"]])

    #     test_value = {'url__gt': 'Kendall', 'age': 25}
    #     result = self.instance.complex_dict_to_sql(test_value)
    #     self.assertListEqual(
    #         result,
    #         [['url', '>', "'Kendall'"], ['url', '=', 25]]
    #     )


if __name__ == '__main__':
    unittest.main()
