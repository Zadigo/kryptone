import itertools
import re
import string
from collections import Counter, defaultdict
from functools import lru_cache

from nltk.tokenize import LineTokenizer, NLTKWordTokenizer
from selenium.webdriver.common.by import By

from kryptone.conf import settings
from kryptone.utils.file_readers import read_document
from kryptone.utils.iterators import drop_null, drop_while

EMAIL_REGEX = r'\S+\@\S+'


class TextMixin:
    """A mixin for analyzing 
    working with text"""

    page_documents = []
    fitted_page_documents = []
    tokenizer_class = NLTKWordTokenizer

    @lru_cache(maxsize=5)
    def _stop_words(self, language='en'):
        if language == 'en':
            path = settings.GLOBAL_KRYPTONE_PATH / 'data/stop_words_english.txt'
        else:
            path = settings.GLOBAL_KRYPTONE_PATH / 'data/stop_words_french.txt'
        data = read_document(path)

        from sklearn.feature_extraction.text import TfidfVectorizer
        tokenizer = TfidfVectorizer().build_tokenizer()
        tokenized_stop_words = [tokenizer(word) for word in data.split('\n')]
        return list(itertools.chain(*tokenized_stop_words))

    @staticmethod
    def get_text_length(text):
        """Get the length of the
        incoming text"""
        return len(text)

    @property
    def _fitted_text_tokens(self):
        result = ' '.join(self.fitted_page_documents)
        return result.split(' ')

    @staticmethod
    def _tokenize(text):
        return list(drop_null(text.split(' ')))
    
    @staticmethod
    def clean_text(text):
        result = str(text).encode('utf-8').decode('utf-8')
        result = result.replace('\n', '')
        return result

    def _remove_punctuation(self, text):
        # We should not replace the "@" in the document since
        # this could affect email extraction
        punctuation = string.punctuation.replace('@', '')
        return text.translate(str.maketrans('', '', punctuation))

    def _remove_stop_words(self, text, language='en'):
        """Removes all stop words from a given document"""
        tokens = self._tokenize(text)
        stop_words = self._stop_words(language=language)
        result = drop_while(lambda x: x in stop_words, tokens)
        return ' '.join(result)

    def _common_words(self, text):
        tokens = self._tokenize(text)
        counter = Counter(tokens)
        return counter.most_common()[1:5]

    def _rare_words(self, text):
        tokens = self._tokenize(text)
        counter = Counter(tokens)
        return counter.most_common()[:-5:-1]

    def fit(self, text):
        """Normalize the document by removing newlines,
        useless spaces, punctuations and removing null
        values"""
        if text is None:
            return None

        normalized_text = str(text).lower().strip()
        if '\n' in normalized_text:
            normalized_text = normalized_text.replace('\n', '')

        text_without_null = ' '.join(drop_null(normalized_text.split(' ')))
        final_text = self._remove_punctuation(text_without_null)
        self.page_documents.append(final_text)
        return final_text

    def fit_transform(self, text=None, language='en'):
        """Fit a document and then transform it into
        a usable element for text analysis"""
        text = self.fit(text)
        if text is not None:
            self.page_documents.append(text)

        from nltk.stem import PorterStemmer
        from nltk.stem.snowball import SnowballStemmer

        if language == 'en':
            stemmer = SnowballStemmer('english')
        elif language == 'fr':
            stemmer = SnowballStemmer('french')
        else:
            stemmer = SnowballStemmer('english')

        for document in self.page_documents:
            result1 = self._remove_stop_words(document)

            # 1. Remove special carachters
            result2 = re.sub('\W', ' ', result1)

            # 2. Remove rare and common words
            rare_words = self._rare_words(result2)
            common_words = self._common_words(result2)
            words_to_remove = rare_words + common_words
            words_to_remove = list(map(lambda x: x[0], words_to_remove))
            simplified_text = drop_while(
                lambda x: x in words_to_remove,
                self._tokenize(result2)
            )
            result3 = ' '.join(simplified_text)

            # 3. Use stemmer to get the stems
            words = re.split('\s+', result3)
            stemmed_words = [stemmer.stem(word=word) for word in words]
            result3 = ' '.join(stemmed_words)

            self.fitted_page_documents.append(result3)
        return self.fitted_page_documents


class SEOMixin(TextMixin):
    """A mixin for auditing a 
    web page"""

    page_audits = defaultdict(dict)
    error_pages = set()

    @property
    def get_page_images(self):
        return self.driver.find_elements(By.TAG_NAME, 'img')

    @property
    def get_page_title(self):
        try:
            script = "return document.querySelector('title').innerText"
            text = self.driver.execute_script(script)
        except:
            return ''
        else:
            return text

    @property
    def get_page_description(self):
        try:
            script = """
            return document.querySelector('meta[name="description"]').attributes.content.textContent
            """
            text = self.driver.execute_script(script)
        except:
            return ''
        else:
            return text

    @property
    def get_page_keywords(self):
        element = self.driver.find_element(
            By.CSS_SELECTOR,
            "meta[name='keywords']"
        )
        try:
            return element.text
        except:
            return ''

    @property
    def has_head_title(self):
        try:
            element = self.driver.find_element(By.TAG_NAME, 'h1')
        except:
            return False
        else:
            return True if element else False

    @property
    def title_is_valid(self):
        return len(self.get_page_title) <= 60

    @property
    def description_is_valid(self):
        return len(self.get_page_title) <= 150

    @property
    def get_transformed_raw_page_text(self):
        text = self.driver.find_element(By.TAG_NAME, 'body').text
        return self.fit(text)

    @property
    def get_page_text(self):
        """Returns a fitted and transformed
        version of the document's text"""
        text = self.driver.find_element(By.TAG_NAME, 'body').text
        return self.fit_transform(text)

    @staticmethod
    def normalize_integers(items):
        # The vectorizer returns int32 integers
        # which crashes the JSON output. Convert
        # these integers to normal ones.
        new_item = {}
        for key, value in items.items():
            new_item[key] = int(value)
        return new_item

    def get_page_status_code(self):
        pass

    def vectorize_documents(self):
        from sklearn.feature_extraction.text import CountVectorizer
        vectorizer = CountVectorizer()
        matrix = vectorizer.fit_transform(self.fitted_page_documents)
        return matrix, vectorizer
    
    def vectorize_page(self, text):
        from sklearn.feature_extraction.text import CountVectorizer
        vectorizer = CountVectorizer()
        matrix = vectorizer.fit_transform(self.fit_transform(text))
        return matrix, vectorizer
    
    def global_audit(self, language='fr'):
        """Returns a global audit of the website"""
        # TODO:
        _, vectorizer = self.vectorize_documents()
        return self.normalize_integers(vectorizer.vocabulary_)
    
    def audit_page(self, current_url, language='fr'):
        """Audit the current page by analyzing different
        key metrics from the title, the description etc."""
        matrix, vectorizer = self.vectorize_page(self.get_page_text)
        vocabulary = self.normalize_integers(vectorizer.vocabulary_)
        audit = {
            'title': self.get_page_title,
            'title_length': self.get_text_length(self.get_page_title),
            'title_is_valid': self.title_is_valid,
            'description': self.get_page_description,
            'description_length': self.get_text_length(self.get_page_description),
            'description_is_valid': self.description_is_valid,
            'url': current_url,
            'page_content_length': len(self.get_page_text),
            'word_count_analysis': vocabulary,
            'status_code': None
        }
        self.page_audits[current_url] = audit
        return audit


class EmailMixin(TextMixin):
    """A mixin for extracting emails
    from a given page"""

    emails_container = set()

    @staticmethod
    def identify_email(value):
        """Checks if the value could be
        an email address"""
        # Skip social media handles
        if value.startswith('@'):
            return None

        if '@' in value:
            return value

        return None

    @staticmethod
    def parse_url(element):
        value = element.get_attribute('href')
        if value is not None and '@' in value:
            return value
        return None

    def parse_protected_email(self, email):
        pass

    def emails(self, text, elements=None):
        """Returns a set of valid email
        addresses on the current page"""
        def validate_values(value):
            if value is None:
                return False

            result = re.match(EMAIL_REGEX, value)
            if result:
                return True

        emails_from_text = self.find_emails_from_links(elements)
        emails_from_links = self.find_emails_from_text(text)
        unvalidated_emails = emails_from_text.union(emails_from_links)

        valid_items = list(filter(validate_values, unvalidated_emails))
        self.emails_container = self.emails_container.union(valid_items)

    def find_emails_from_text(self, text):
        """Return emails embedded in plain text"""
        fitted_text = self.fit(text)
        emails_from_text = map(self.identify_email, self._tokenize(fitted_text))
        return set(emails_from_text)

    def find_emails_from_links(self, elements):
        """Return emails present in links"""
        emails_from_urls = map(self.parse_url, elements)
        return set(emails_from_urls)
