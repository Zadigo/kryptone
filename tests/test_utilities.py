import unittest
from bs4 import BeautifulSoup

from kryptone.utils.text import Text


class TestTextUtility(unittest.TestCase):
    def setUp(self):
        with open('tests/pages/novencia.html', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        self.instance = Text(soup.text)

    def test_text_structure(self):
        self.assertIsInstance(str(self.instance), str)


if __name__ == '__main__':
    unittest.main()
