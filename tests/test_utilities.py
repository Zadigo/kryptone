import pathlib
import unittest

from bs4 import BeautifulSoup

from kryptone.utils.functions import (directory_from_breadcrumbs,
                                      directory_from_url)
from kryptone.utils.text import Text
from kryptone.utils.urls import URL


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

    def test_dierectory_from_url_with_query(self):
        url = URL(
            'https://www.bershka.com/fr/femme/vetements/robes-n3802.html?tipology=1010193338%7C%7C1010193337&sort=1'
        )
        result = directory_from_url(url)
        self.assertEqual(result, pathlib.Path('fr/femme/vetements'))


class TestTextUtilities(unittest.TestCase):
    def test_text_class(self):
        with open('tests/pages/novencia.html', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            instance = Text(soup.text)
            print(instance)
            self.assertIsInstance(str(instance), str)


if __name__ == '__main__':
    unittest.main()
