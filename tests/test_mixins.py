import unittest
from kryptone.mixins import TextMixin, EmailMixin
from kryptone.utils import read_document


# class TestTextMixin(unittest.TestCase):
#     def setUp(self):
#         # data = read_document('data/text.txt')
#         self.instance = TextMixin()

#     def test_text_length(self):
#         text = 'Good text'
#         value = self.instance.get_text_length(text)
#         self.assertEqual(value, 9)

#     def test_tokenize(self):
#         text = 'Good text'
#         value = self.instance.tokenize(text)
#         self.assertListEqual(value, ['Good', 'text'])

#     def test_vectorization(self):
#         text = 'Good text'
#         value = self.instance.vectorize(text)
#         self.assertDictEqual(value, {'good': 0, 'text': 1})


class TestEmailMixin(unittest.TestCase):
    def setUp(self):
        self.text = 'test@google.com'
        self.instance = EmailMixin()

    def test_email_identification(self):
        result = self.instance.identify_email(self.text)
        self.assertIsNotNone(result)
        self.assertEqual(result, 'test@google.com')

    def test_find_email_from_text(self):
        text = 'this is a text with an email: test@gmail.com'
        emails = self.instance.find_emails_from_text(text)
        self.assertListEqual(list(emails), ['test@gmail.com'])


if __name__ == '__main__':
    unittest.main()
