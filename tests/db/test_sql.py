import unittest
from kryptone.db.backends import SQL


class TestSQL(unittest.TestCase):
    def setUp(self):
        self.instance = SQL()

    def test_complex_dict_to_sql(self):
        test_value = {'url__gt': 'Kendall'}
        result = self.instance.complex_dict_to_sql(test_value)
        self.assertListEqual(result, [['url', '>', "'Kendall'"]])

        test_value = {'url__gt': 'Kendall', 'age': 25}
        result = self.instance.complex_dict_to_sql(test_value)
        self.assertListEqual(
            result,
            [['url', '>', "'Kendall'"], ['url', '=', 25]]
        )


if __name__ == '__main__':
    unittest.main()
