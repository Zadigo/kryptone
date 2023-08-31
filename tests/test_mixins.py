import unittest
import string
import requests
from bs4 import BeautifulSoup

from kryptone.mixins import EmailMixin, SEOMixin, TextMixin

with open('tests/pages/etam.html', encoding='utf-8') as f:
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
        for item in ['\n', '\r']:
            with self.subTest(item=item):
                self.assertNotIn(item, result)

        punctuation = string.punctuation.replace('@', '')
        for punctuation in punctuation:
            with self.subTest(punctuation=punctuation):
                self.assertFalse(punctuation in result)

        self.assertTrue(result.islower())

    def test_fit_transform(self):
        pass
        # result = self.mixin.fit_transform(
        #     text=self.text,
        #     language='fr'
        # )
        # self.assertGreater(len(result), 0)

    def test_rare_words(self):
        text = self.mixin.fit(self.text)
        result1 = self.mixin._rare_words(text)
        result2 = self.mixin._common_words(text)
        self.assertIsInstance(result1, list)
        self.assertIsInstance(result2, list)

    def test_stop_words_removal(self):
        # Test that we have effectively removed all
        # stop words from the text content
        fitted_text = self.mixin.fit(self.text)
        result = self.mixin._remove_stop_words(fitted_text, language='fr')

        tokens = self.mixin._tokenize(result)
        for token in tokens:
            with self.subTest(token=token):
                self.assertNotEqual(token, self.mixin._stop_words())


class TestSEOMixin(unittest.TestCase):
    def setUp(self):
        self.mixin = SEOMixin()

    def test_integrity(self):
        self.mixin.audit_page()


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


# if __name__ == '__main__':
#     unittest.main()


# mixin = TextMixin()
# text = soup.find('body').text
# mixin.clean_text(text)
# text = mixin.fit(text)
# print(mixin.stop_words())
# text = mixin.fit(soup.text)


# def remove_numbers(token):
#     if token.isdigit():
#         return False
#     return True


# text = mixin.fit_transform(
#     text=text, language='fr',
#     use_multipass=True,
#     text_processors=[remove_numbers]
# )
# # text = mixin._remove_stop_words_multipass(text)
# # text = mixin._rare_words(text)
# print(text)

# # with open('text.txt', mode='w', encoding='utf-8') as f:
#     f.write(text)
