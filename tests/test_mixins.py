import unittest

import requests
from bs4 import BeautifulSoup

from kryptone.mixins import EmailMixin, TextMixin

with open('tests/pages/bershka.html', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')


class TestTextMixin(unittest.TestCase):
    def setUp(self):
        self.text = soup.text
        self.mixin = TextMixin()

    def test_fit(self):
        # Expected: text should be lowered, no extra spaces,
        # \n, \r and \s should be removed, html tags should
        # also be removed
        result = self.mixin.fit(self.text)
        for item in ['\n']:
            with self.subTest(item=item):
                self.assertNotIn(item, result)

    def test_fit_transform(self):
        result = self.mixin.fit_transform(
            text=self.text,
            language='fr'
        )
        self.assertGreater(len(result), 0)

    def test_rare_words(self):
        text = self.mixin.fit(self.text)
        result1 = self.mixin._rare_words(text)
        result2 = self.mixin._common_words(text)
        self.assertIsInstance(result1, list)
        self.assertIsInstance(result2, list)

    # def test_stop_words_removal(self):
    #     # Test that we have effectively removed all
    #     # stop words from the text content
    #     result = self.mixin._remove_stop_words(self.text)
    #     for stop_word in self.mixin._stop_words():
    #         with self.subTest(stop_word=stop_word):
    #             self.assertNotIn(stop_word, result)


# class TestEmailMixin(unittest.TestCase):
#     def setUp(self):
#         self.text = 'test@google.com'
#         self.instance = EmailMixin()

#     def test_email_identification(self):
#         result = self.instance.identify_email(self.text)
#         self.assertIsNotNone(result)
#         self.assertEqual(result, 'test@google.com')

#     def test_find_email_from_text(self):
#         text = 'this is a text with an email: test@gmail.com'
#         emails = self.instance.find_emails_from_text(text)
#         self.assertListEqual(list(emails), ['test@gmail.com'])


if __name__ == '__main__':
    unittest.main()
