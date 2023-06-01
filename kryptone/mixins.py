import re
from collections import defaultdict
from functools import lru_cache

from nltk.stem import PorterStemmer
from nltk.tokenize import LineTokenizer, NLTKWordTokenizer
from selenium.webdriver.common.by import By
from sklearn.feature_extraction.text import CountVectorizer

from kryptone import PROJECT_PATH

EMAIL_REGEX = r'\S+\@\S+'


class TextMixin:
    """A mixin for analyzing 
    working with text"""

    page_documents = []
    tokenizer_class = NLTKWordTokenizer

    @staticmethod
    def get_text_length(text):
        """Get the length of the
        incoming text"""
        return len(text)

    @lru_cache(maxsize=100)
    def get_stop_words(self, language='fr'):
        filename = 'stop_words_french' if language == 'fr' else 'stop_words_english'
        file_path = PROJECT_PATH / f'kryptone/data/{filename}.txt'
        with open(file_path, mode='r', encoding='utf-8') as f:
            stop_words = ''.join(f.readlines())

            tokenizer = LineTokenizer()
            stop_words = tokenizer.tokenize(stop_words)
        return stop_words

    def clean_html_text(self, raw_text):
        tokenizer = LineTokenizer()
        tokens = tokenizer.tokenize(raw_text)
        text = ' '.join(tokens)
        return text

    def vectorize_pages(self, raw_text):
        """Return the most common words from the website
        by continuously building the page_documents and
        analyzing their content"""
        def text_preprocessor(text):
            porter_stemmer = PorterStemmer()

            # Remove special carachters
            text = re.sub("\\W", " ", text)

            # Use stem words
            # words = re.split('\s+', text)
            # stemmed_words = [porter_stemmer.stem(word=word) for word in words]
            # return ' '.join(stemmed_words)

            # text = text.lower()
            # text = re.sub("\\W", " ", text)  # remove special chars
            # text = re.sub("\\s+(in|the|all|for|and|on)\\s+",
            #             " _connector_ ", text)  # normalize certain words

            # # stem words
            # words = re.split("\\s+", text)
            # stemmed_words = [porter_stemmer.stem(word=word) for word in words]
            # return ' '.join(stemmed_words)
            return text

        text = self.clean_html_text(raw_text)
        self.page_documents.append(text)

        vectorizer = CountVectorizer(
            stop_words=self.get_stop_words(),
            max_features=50,
            preprocessor=text_preprocessor,
            # max_df=0.85
        )
        matrix = vectorizer.fit_transform(self.page_documents)
        return matrix, vectorizer.vocabulary_

    def vectorize_page(self, raw_text, language='fr'):
        text = self.clean_html_text(raw_text)
        vectorizer = CountVectorizer(
            stop_words=self.get_stop_words(language=language),
            max_features=20
        )
        matrix = vectorizer.fit_transform([text])
        return matrix, vectorizer.vocabulary_

    def tokenize(self, text):
        """Create word tokens from a text"""
        instance = self.tokenizer_class()
        return instance.tokenize(text)


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
            script = """return document.querySelector('meta[name="description"]').attributes.content.textContent"""
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
    def get_page_text(self):
        return self.driver.find_element(By.TAG_NAME, 'body').text

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

    def global_audit(self, language='fr'):
        _, vocabulary = self.vectorize_pages(self.get_page_text)
        return self.normalize_integers(vocabulary)

    def audit_page(self, current_url, language='fr'):
        """Audit the current page by analyzing different
        key metrics from the title, the description etc."""
        _, vocabulary = self.vectorize_page(
            self.get_page_text, language=language)
        vocabulary = self.normalize_integers(vocabulary)
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
        emails_from_text = map(self.identify_email, self.tokenize(text))
        return set(emails_from_text)

    def find_emails_from_links(self, elements):
        """Return emails present in links"""
        emails_from_urls = map(self.parse_url, elements)
        return set(emails_from_urls)
