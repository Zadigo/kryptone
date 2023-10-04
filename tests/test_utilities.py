import pathlib
import unittest
from bs4 import BeautifulSoup

from kryptone.utils.text import Text
from kryptone.utils.functions import directory_from_breadcrumbs, directory_from_url


class TestFunctions(unittest.TestCase):
    def test_directory_from_breadcrumbs(self):
        text = "Bébé fille > T-shirt, polo, sous pull > T-shirt manches longues en coton bio à message printé"
        result = directory_from_breadcrumbs(text)
        self.assertIsInstance(result, pathlib.Path)
        self.assertEqual(str(result), 'bébé_fille\\tshirt_polo_sous_pull')

    def test_directory_from_url(self):
        path = '/ma/woman/clothing/dresses/short-dresses/shirt-dress-1.html'
        result = directory_from_url(path, exclude=['ma'])
        self.assertIsInstance(result, pathlib.Path)
        self.assertEqual(
            str(result),
            'woman\\clothing\\dresses\\shortdresses'
        )


class TestTextUtilities(unittest.TestCase):
    def test_text_class(self):
        with open('tests/pages/novencia.html', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            instance = Text(soup.text)
            print(instance)
            self.assertIsInstance(str(instance), str)


if __name__ == '__main__':
    unittest.main()
