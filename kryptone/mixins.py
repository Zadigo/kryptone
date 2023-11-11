import requests
import json
import re
import time
import secrets
import string
from collections import Counter, defaultdict
from functools import cached_property, lru_cache
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from kryptone.utils.text import clean_text, remove_punctuation, remove_accents
from kryptone.conf import settings
from kryptone.utils.date_functions import get_current_date
from kryptone.utils.file_readers import read_document
from kryptone.utils.iterators import drop_null, drop_while, keep_while

EMAIL_REGEX = r'\S+\@\S+'


class TextMixin:
    page_documents = []
    fitted_page_documents = []

    @lru_cache(maxsize=10)
    def stop_words(self, language='en'):
        global_path = settings.GLOBAL_KRYPTONE_PATH
        if language == 'en':
            file_language = 'english'
        elif language == 'fr':
            file_language = 'french'
        filename = global_path / f'data/stop_words_{file_language}.txt'
        return read_document(filename, as_list=True)

    @cached_property
    def stop_words_html(self):
        global_path = settings.GLOBAL_KRYPTONE_PATH
        filename = global_path / 'data/html_tags.txt'
        return read_document(filename, as_list=True)

    @staticmethod
    def tokenize(text):
        return text.split(' ')

    def _common_words(self, tokens):
        counter = Counter(tokens)
        return counter.most_common()[1:5]

    def _rare_words(self, tokens):
        counter = Counter(tokens)
        return counter.most_common()[:-5:-1]

    def _remove_stop_words(self, tokens, language='en'):
        """Removes all stop words from a given document"""
        stop_words = self.stop_words(language=language)
        for token in tokens:
            if token in stop_words:
                continue
            yield token

    def _remove_stop_words_multipass(self, tokens):
        """Remove stop words from a given document
        against both french and english language"""
        english_stop_words = self.stop_words(language='en')
        french_stop_words = self.stop_words(language='fr')
        html_stop_words = self.stop_words_html

        stop_words = english_stop_words + french_stop_words + html_stop_words
        for token in tokens:
            if token in stop_words:
                continue
            yield token

    def get_page_text(self):
        """Returns a fitted version of 
        the document's text"""
        script = """
        return document.body.outerHTML
        """
        html = self.driver.execute_script(script)
        soup = BeautifulSoup(html, 'html.parser')
        script_tags = [tag.extract() for tag in soup.find_all('script')]
        return self.fit(soup.text)

    def fit_transform(self, text=None, language='en', use_multipass=False):
        if text is not None:
            text = self.fit(text)

        # from nltk.stem import PorterStemmer
        from nltk.stem.snowball import SnowballStemmer

        stemmer = SnowballStemmer('english')
        if language == 'fr':
            stemmer = SnowballStemmer('french')

        cleaned_texts = []
        for document in self.page_documents:
            tokens = self.tokenize(document)
            # 1. Remove stop words first because
            # after we will normalizing the text
            if use_multipass:
                tokens = list(self._remove_stop_words_multipass(tokens))
            else:
                tokens = list(self._remove_stop_words(tokens, language=language))

            # 2. Remove rare and common words
            rare_words = self._rare_words(tokens)
            common_words = self._common_words(tokens)
            words_to_remove = rare_words + common_words
            common_words_to_remove = list(
                map(lambda x: list(x)[0], words_to_remove)
            )

            simplified_tokens = list(drop_while(
                lambda x: x in common_words_to_remove,
                tokens
            ))
            text = ' '.join(simplified_tokens)
            cleaned_texts.append(text)

        for text in cleaned_texts:
            text = remove_accents(text)
            self.fitted_page_documents.append(text)
        return self.fitted_page_documents

    def fit(self, raw_text, email_exception=False):
        """Normalize the document by removing newlines,
        useless spaces, special characters, punctuations 
        and null values. The fit method fits the text 
        before running in depth text transformation"""
        if raw_text is None:
            return None

        cleaned_text = clean_text(raw_text)
        text = cleaned_text.lower()
        text = re.sub('\W', ' ', text)
        self.page_documents.append(text)
        return remove_punctuation(text, email_exception=email_exception)


class SEOMixin(TextMixin):
    pass


class EmailMixin(TextMixin):
    pass


# class TestClass(TextMixin):
#     def __init__(self):
#         self.driver = None

#     def start(self):
#         self.driver = get_selenium_browser_instance(browser_name='Edge')
#         self.driver.get('https://www.noiise.com/agences/lille/')
#         print(self.fit_transform())
#         time.sleep(10)


# c = TestClass()
# # c.start()


response = requests.get('https://www.noiise.com/agences/lille/')
s = BeautifulSoup(response.content, 'html.parser')
r = [tag.extract() for tag in s.find_all('script')]
m = TextMixin()
print(m.fit_transform(s.text, language='fr'))
