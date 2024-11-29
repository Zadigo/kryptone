import pathlib
import unittest

from kryptone.utils.functions import (create_filename,
                                      directory_from_breadcrumbs,
                                      directory_from_url)
from kryptone.utils.urls import URL


class TestFunctions(unittest.TestCase):
    def test_create_filename(self):
        self.assertIsInstance(create_filename(), str)

        self.assertTrue(
            create_filename(
                extension='google'
            ).startswith('google-')
        )

    def test_directory_from_breadcrumb(self):
        result = directory_from_breadcrumbs('a > b > c', separator='>')
        self.assertEqual(result, pathlib.Path('a/b'))

        result = directory_from_breadcrumbs('a > b > c > d', exclude=['b'])
        self.assertEqual(result, pathlib.Path('a/c'))

    def test_build_directory(self):
        urls = [
            '/fr/femme/vetements/robes-n3802.html?tipology=1010193338%7C%7C1010193337&sort=1',
            URL('https://www.bershka.com/fr/femme/vetements/robes-n3802.html?tipology=1010193338%7C%7C1010193337&sort=1')
        ]
        for url in urls:
            with self.subTest(url=url):
                result = directory_from_url(url)
                self.assertEqual(result, pathlib.Path('fr/femme/vetements'))
