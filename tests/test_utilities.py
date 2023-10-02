import unittest
from bs4 import BeautifulSoup

from kryptone.utils.text import Text


class TestTextUtility(unittest.TestCase):
    def setUp(self):
        with open('kryptone/tests/pages/novencia.html', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        self.instance = Text(soup.text)

    def test_text_structure(self ):
        print(self.instance)


if __name__ == '__main__':
    unittest.main()
