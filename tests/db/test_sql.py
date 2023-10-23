import pathlib
import unittest

from kryptone.conf import settings
from kryptone.db.backends import SQL
from kryptone.db.backends import Lower

settings['PROJECT_PATH'] = pathlib.Path(__file__).parent.parent.absolute().joinpath('testproject')


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

    def test_build_script(self):
        values = ['a', 'b']
        result = self.instance.build_script(*values)
        self.assertTrue(result, """a;\nb;""")

    def test_decompose_filters(self):
        arguments = [
            [{'name__eq': 'Kendall'}, [('name', '=', 'Kendall')]],
            [{'name__lt': 'Kendall'}, [('name', '<', 'Kendall')]],
            [{'name__gt': 'Kendall'}, [('name', '>', 'Kendall')]],
            [{'name__lte': 'Kendall'}, [('name', '<=', 'Kendall')]],
            [{'name__gte': 'Kendall'}, [('name', '>=', 'Kendall')]],
            [{'name__contains': 'Kendall'}, [('name', 'like', 'Kendall')]],
            [{'name__startswith': 'Kendall'}, [('name', 'startswith', 'Kendall')]],
            [{'name__endswith': 'Kendall'}, [('name', 'endswith', 'Kendall')]],
            [{'name__range': 'Kendall'}, [('name', 'between', 'Kendall')]],
            [{'name__ne': 'Kendall'}, [('name', '!=', 'Kendall')]],
            [{'name__in': 'Kendall'}, [('name', 'in', 'Kendall')]],
            [{'name__isnull': 'Kendall'}, [('name', 'isnull', 'Kendall')]]
        ]

        for argument in arguments:
            with self.subTest(argument=argument):
                result = self.instance.decompose_filters(**argument[0])
                self.assertListEqual(result, argument[1])

    def test_build_filters(self):
        arguments = [
            [[('name', '=', 'Kendall')], ["name = 'Kendall'"]],
            [[('name', '!=', 'Kendall')], ["name != 'Kendall'"]],
            [[('name', '<', '1')], ["name < '1'"]],
            [[('name', '>', '1')], ["name > '1'"]],
            [[('name', '<=', '1')], ["name <= '1'"]],
            [[('name', '>=', '1')], ["name >= '1'"]],
            [[('name', 'like', 'Kendall')], ["name like '%Kendall%'"]],
            [[('name', 'startswith', 'Kendall')], ["name like 'Kendall%'"]],
            [[('name', 'endswith', 'Kendall')], ["name like '%Kendall'"]],
            [[('name', 'between', [1, 2])], ["between 1 and 2"]],
            [[('name', 'in',  ['Kendall', 'Kylie'])], ["name in ('Kendall', 'Kylie')"]],
            # TODO: Implement
            # [[('name', 'isnull', 'Kendall')], ["name = '1'"]]
        ]

        for argument in arguments:
            with self.subTest(argument=argument):
                result = self.instance.build_filters(argument[0])
                self.assertListEqual(result, argument[1])


    def test_build_annotations(self):
        arguments = [
            [{'name': Lower('name')}, ['lower(name) as name']]
        ]
        for argument in arguments:
            with self.subTest(argument=argument):
                result = self.instance.build_annotation(**argument[0])
                self.assertListEqual(result, argument[1])

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


if __name__ == '__main__':
    unittest.main()
