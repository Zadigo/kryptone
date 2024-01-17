import unittest

from kryptone.utils.iterators import PagePaginationGenerator, URLGenerator


class TestUrlGenerator(unittest.TestCase):
    template = 'https://www.maxizoo.fr/c/chien/nourriture-pour-chien/'
    
    # def test_function(self):
    #     result = URLGenerator(self.template, params={'$page': 'k'}, k=2, start=1)
    #     expected_result = [
    #         'https://www.maxizoo.fr/c/chien/nourriture-pour-chien/?currentPage=1',
    #         'https://www.maxizoo.fr/c/chien/nourriture-pour-chien/?currentPage=2'
    #     ]
    #     self.assertListEqual(list(result), expected_result)

    def test_pagination_iterator(self):
        instance = PagePaginationGenerator(self.template, k=2)
        urls = [
            'https://www.maxizoo.fr/c/chien/nourriture-pour-chien/?page=1',
            'https://www.maxizoo.fr/c/chien/nourriture-pour-chien/?page=2'
        ]
        self.assertListEqual(list(instance), urls)


if __name__ == '__main__':
    unittest.main()
