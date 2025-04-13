import pathlib
import string
from unittest import TestCase
from unittest.mock import patch
from nltk.corpus import stopwords
from kryptone.contrib.seo import TextMixin, TFIDFProcessor


class TestTextMixin(TestCase):
    @classmethod
    def setUpClass(cls):
        path = pathlib.Path('.').resolve()
        data_folder = path.joinpath('tests', 'data')

        with open(data_folder.joinpath('html1.html'), mode='r', encoding='utf-8') as f:
            cls.document_data = f.read()

        cls.final_data = None

    def tearDown(self):
        super().tearDown()
        path = pathlib.Path('.').resolve()
        data_folder = path.joinpath('tests')

        with open(data_folder.joinpath('final_data.txt'), mode='w', encoding='utf-8') as f:
            f.write(self.final_data)

    @patch.object(TextMixin, 'driver', create=True)
    def test_fit_transform(self, mock_driver):
        mock_driver.execute_script.return_value = self.document_data

        instance = TextMixin()
        instance.nltk_downloads = True
        result = instance.fit_transform(instance.get_page_text())
        self.final_data = result

        punctuation = string.punctuation.replace('@', '')
        for punctuation in punctuation:
            with self.subTest(punctuation=punctuation):
                self.assertFalse(punctuation in result)

        self.assertTrue(result.islower())

        tokens = result.split(' ')
        stop_words = stopwords.words('english') + stopwords.words('french')

        for token in tokens:
            with self.subTest(token=token):
                truth_array = map(lambda x: token == x, stop_words)
                self.assertFalse(all(list(truth_array)))


class TestTFIDFProcessor(TestCase):
    @classmethod
    def setUpClass(cls):
        path = pathlib.Path('.').resolve()
        data_folder = path.joinpath('tests', 'data')

        with open(data_folder.joinpath('text.txt'), mode='r', encoding='utf-8') as f:
            cls.document = f.read()

        cls.instance = TFIDFProcessor(documents=[cls.document])

    def test_calculate_tf(self):
        result = self.instance._calculate_tf(self.document)
        self.assertIsInstance(result, dict)

    def test_calculate_idf(self):
        result = self.instance._calculate_idf()
        self.assertIsInstance(result, dict)

    def test_compute_tfidf(self):
        result = self.instance.compute_tfidf()
        print(result)
        self.assertIsInstance(result, dict)

    def test_preprocess_text_with_tfidf(self):
        result = self.instance.preprocess_text_with_tfidf(keep_top_n=10)
        print(result)
        self.assertIsInstance(result, list)
