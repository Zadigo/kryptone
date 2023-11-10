import json
import re
import secrets
import string
from collections import Counter, defaultdict
from functools import cached_property, lru_cache
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from kryptone.conf import settings
from kryptone.utils.date_functions import get_current_date
from kryptone.utils.file_readers import read_document
from kryptone.utils.iterators import drop_null, drop_while, keep_while

EMAIL_REGEX = r'\S+\@\S+'


class TextMixin:
    """A mixin for analyzing text"""

    page_documents = []
    fitted_page_documents = []

    @cached_property
    def stop_words_english(self):
        global_path = settings.GLOBAL_KRYPTONE_PATH
        filename = global_path / 'data/stop_words_english.txt'
        return read_document(filename, as_list=True)

    @cached_property
    def stop_words_french(self):
        global_path = settings.GLOBAL_KRYPTONE_PATH
        filename = global_path / 'data/stop_words_french.txt'
        return read_document(filename, as_list=True)

    @cached_property
    def stop_words_html(self):
        global_path = settings.GLOBAL_KRYPTONE_PATH
        filename = global_path / 'data/html_tags.txt'
        return read_document(filename, as_list=True)

    @lru_cache(maxsize=10)
    def stop_words(self, language='en'):
        natural_language_stop_words = self.stop_words_english if language == 'en' else self.stop_words_french
        data = natural_language_stop_words + self.stop_words_html
        return list(drop_null(data))

        # regular_language_stop_words = read_document(path)
        # html_names_stop_words = read_document(
        #     global_path / 'data/html_tags.txt'
        # )
        # data = regular_language_stop_words.split('\n')
        # data.extend(html_names_stop_words.split('\n'))
        # return list(drop_null(data))

        # from sklearn.feature_extraction.text import TfidfVectorizer
        # tokenizer = TfidfVectorizer().build_tokenizer()
        # tokenized_stop_words = [tokenizer(word) for word in data]
        # return list(itertools.chain(*tokenized_stop_words))

    @staticmethod
    def get_text_length(text):
        """Get the length of the
        incoming text"""
        if text is None:
            return 0
        return len(text)

    @property
    def _fitted_text_tokens(self):
        result = ' '.join(self.fitted_page_documents)
        return result.split(' ')

    @staticmethod
    def _tokenize(text):
        tokens = text.split(' ')
        return list(drop_null(tokens))

    @staticmethod
    def simple_clean_text(text, encoding='utf-8'):
        """Applies simple cleaning techniques on the
        text by removing newlines, lowering the characters
        and removing extra spaces"""
        lowered_text = str(text).lower().strip()
        text = lowered_text.encode(encoding).decode(encoding)
        normalized_text = text.replace('\n', ' ')
        return normalized_text.strip()

    def _remove_punctuation(self, text):
        # We should not replace the "@" in the document since
        # this could affect email extraction
        punctuation = string.punctuation.replace('@', '')
        return text.translate(str.maketrans('', '', punctuation))

    def _remove_stop_words(self, text, language='en'):
        """Removes all stop words from a given document"""
        tokens = self._tokenize(text)
        stop_words = self.stop_words(language=language)
        result = drop_while(lambda x: x in stop_words, tokens)
        return ' '.join(result)

    def _remove_stop_words_multipass(self, text):
        """Remove stop words from a given document
        against both french and english language"""
        tokens = self._tokenize(text)

        stop_words = self.stop_words_english + \
            self.stop_words_french + self.stop_words_html
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

    def _run_processors(self, tokens, processors):
        if processors:
            new_tokens = []
            for processor in processors:
                if not callable(processor):
                    continue

                for token in tokens:
                    result = processor(token)
                    # Processors should return a boolean.
                    # On fail, just return the token as is
                    if not isinstance(result, bool):
                       new_tokens.append(token)

                    if result:
                        new_tokens.append(token)
        else:
            return tokens

    def normalize_spaces(self, text):
        return ' '.join(self._tokenize(text))
    
    def validate_text(self, text):
        if text is None:
            return ''
        return text

    def fit(self, text):
        """Normalize the document by removing newlines,
        useless spaces, special characters, punctuations 
        and null values. The fit method fits the text 
        before running in depth text transformation"""
        if text is None:
            return None

        text = re.sub('\W', ' ', text)
        normalized_text = self.simple_clean_text(text)
        final_text = self.normalize_spaces(
            self._remove_punctuation(normalized_text)
        )
        self.page_documents.append(final_text)
        return final_text

    def fit_transform(self, text=None, language='en', use_multipass=False, text_processors=[]):
        """Fit a document and then transform it into
        a usable element for text analysis"""
        fitted_text = self.fit(text)
        if fitted_text is not None:
            self.page_documents.append(fitted_text)

        from nltk.stem import PorterStemmer
        from nltk.stem.snowball import SnowballStemmer

        if language == 'en':
            stemmer = SnowballStemmer('english')
        elif language == 'fr':
            stemmer = SnowballStemmer('french')
        else:
            stemmer = SnowballStemmer('english')

        for document in self.page_documents:
            # 1. Remove stop words
            if use_multipass:
                result1 = self._remove_stop_words_multipass(document)
            else:
                result1 = self._remove_stop_words(document, language=language)

            # 2. Remove special carachters
            # result2 = re.sub('\W', ' ', result1)

            # 3. Remove rare and common words
            rare_words = self._rare_words(result1)
            common_words = self._common_words(result1)

            words_to_remove = rare_words + common_words
            words_to_remove = list(map(lambda x: list(x)[0], words_to_remove))

            tokenized_text = self._tokenize(result1)
            simplified_text = list(drop_while(
                lambda x: x in words_to_remove,
                tokenized_text
            ))

            # 4. Run custom text processors
            simplified_text = self._run_processors(
                simplified_text, text_processors
            )

            # 5. Use stemmer
            stemmed_words = [
                stemmer.stem(word=word)
                for word in simplified_text
            ]
            result3 = ' '.join(stemmed_words)

            self.fitted_page_documents.append(result3)
        return self.fitted_page_documents


class SEOMixin(TextMixin):
    """A mixin for auditing a web page"""

    raw_texts = []
    error_pages = set()
    text_by_page = defaultdict(str)
    page_audits = defaultdict(dict)

    @property
    def get_page_title(self):
        script = """
        let el = document.querySelector('title')
        return el && el.textContent
        """
        text = self.driver.execute_script(script)
        return self.fit(text)

    @property
    def get_page_description(self):
        script = """
        let el = document.querySelector('meta[name="description"]')
        return el && el.attributes.content.textContent
        """
        text = self.driver.execute_script(script)
        return self.fit(self.validate_text(text))

    @property
    def get_page_text(self):
        """Returns a fitted and transformed
        version of the document's text"""
        script = """
        return document.body.outerHTML
        """
        html = self.driver.execute_script(script)
        soup = BeautifulSoup(html, 'html.parser')
        script_tags = [tag.extract() for tag in soup.find_all('script')]
        return self.fit(soup.text)
    
    @property
    def get_page_keywords(self):
        script = """
        let el = document.querySelector('[name="keywords"]')
        return el && el.content || ''
        """
        text = self.driver.execute_script(script)
        return self.fit(self.validate_text(text))

    @property
    def has_head_title(self):
        return all([
            self.get_page_title is not None,
            self.get_page_title != ''
        ])

    @property
    def title_is_valid(self):
        page_title = self.get_page_title
        if page_title is None:
            return False
        return len(page_title) <= 60

    @property
    def description_is_valid(self):
        page_description = self.get_page_description
        if page_description is None:
            return False
        return len(page_description) <= 150

    
    @property
    def get_grouped_text(self):
        """Returns a fitted and transformed version
        of the document's text including keywords
        and description"""
        body_text = self.get_page_text
        description = self.get_page_description
        keywords = self.get_page_keywords
        return ' '.join([body_text, description, keywords])

    @staticmethod
    def normalize_integers(items):
        # The vectorizer returns int32 integers
        # which crashes the JSON output. Convert
        # these integers to normal ones.
        new_item = {}
        for key, value in items.items():
            new_item[key] = int(value)
        return new_item
        
    @cached_property
    def page_speed_script(self):
        path = settings.GLOBAL_KRYPTONE_PATH.joinpath(
            'data', 'js', 'page_speed.js'
        )
        with open(path, encoding='utf-8') as f:
            content = f.read()
        return content
    
    def get_page_speed(self, audit):
        result = self.driver.execute_script(self.page_speed_script)
        audit['timing'] = result

    def get_page_status_code(self):
        pass

    def get_internal_urls(self, audit):
        script = """
        return Array.from(document.querySelectorAll('a')).map(x => x.href).filter(x => x !== "")
        """
        urls = self.driver.execute_script(script)
        filtered_urls = filter(lambda x: urlparse(x).netloc == self._start_url_object.netloc, urls)
        audit['internal_urls'] = len(list(filtered_urls))
    
    def audit_images(self, audit):
        """Checks that the images of the current
        page has ALT attributes to them"""
        image_alts = []
        script = """
        return document.querySelectorAll('img')
        """
        images = self.driver.execute_script(script)
        if images:
            while images:
                try:
                    image = images.pop()
                    image_alt = self.fit(image.get_attribute('alt'))
                except:
                    pass
                else:
                    image_alts.append(image_alt)
            empty_alts = list(keep_while(lambda x: x == '', image_alts))

            unique_image_alts = set(image_alts)
            percentage_count = (len(empty_alts) / len(image_alts)) * 100
            percentage_invalid_images = round(percentage_count, 2)

            audit['pct_images_with_no_alt'] = percentage_invalid_images
            audit['image_alts'] = list(unique_image_alts)
            return percentage_invalid_images, unique_image_alts
        else:
            audit['pct_images_with_no_alt'] = 0
            audit['image_alts'] = []
            return 0, set()
    
    def audit_structured_data(self, audit):
        """
        Checks if the website has structured data

        >>> self.audit_structured_data({})
        ... True, {}
        """
        has_structured_data = False
        structured_data_type = None
        script = """
        let el = document.querySelector('script[type*="ld+json"]')
        return el && el.textContent
        """
        content = self.driver.execute_script(script)
        if content:
            content = json.loads(content)
            has_structured_data = True
            # Try to get @type otherwise just return the content
            structured_data_type = content.get('@type', None) or content

        audit['has_structured_data'] = has_structured_data
        audit['structured_data_type'] = structured_data_type
        return has_structured_data, structured_data_type

    def vectorize_documents(self):
        from sklearn.feature_extraction.text import CountVectorizer
        vectorizer = CountVectorizer()
        matrix = vectorizer.fit_transform(self.fitted_page_documents)
        return matrix, vectorizer

    def vectorize_page(self, text):
        from sklearn.feature_extraction.text import CountVectorizer
        vectorizer = CountVectorizer()
        self.raw_texts.append(text)
        transformed_text = self.fit_transform(
            text=text, 
            language=settings.WEBSITE_LANGUAGE
        )
        matrix = vectorizer.fit_transform(transformed_text)
        return matrix, vectorizer

    def global_audit(self):
        """Returns the global audit for all the
        pages that have already been audited 
        on the website"""
        # TODO:
        _, vectorizer = self.vectorize_documents()
        vocabulary = vectorizer.vocabulary_
        return self.normalize_integers(vocabulary)

    def audit_page(self, current_url):
        """Audit the current page by analyzing different
        key metrics from the title, the description etc."""  
        grouped_text = self.get_grouped_text
        self.text_by_page[str(current_url)] = grouped_text

        matrix, vectorizer = self.vectorize_page(grouped_text)
        vocabulary = self.normalize_integers(vectorizer.vocabulary_)

        script = """
        let el = document.querySelector('h1')
        return el && el !== null
        """
        has_head_title = self.driver.execute_script(script)

        if not has_head_title:
            self.driver.save_screenshot(f'media/no_h1_{secrets.token_hex(nbytes=5)}.png')

        audit = {
            'date': get_current_date(),
            'title': self.get_page_title,
            'title_length': self.get_text_length(self.get_page_title),
            'title_is_valid': self.title_is_valid,
            'description': self.get_page_description,
            'description_length': self.get_text_length(self.get_page_description),
            'description_is_valid': self.description_is_valid,
            'url': str(current_url),
            'page_content_length': len(self.get_page_text),
            # 'word_count_analysis': vocabulary,
            'status_code': None,
            'is_https': current_url.is_secured,
            'has_h1': has_head_title
        }
        
        self.audit_structured_data(audit)
        self.audit_images(audit)
        self.get_page_speed(audit)
        self.get_internal_urls(audit)

        self.page_audits[str(current_url)] = audit
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
        emails_from_text = map(self.identify_email,
                               self._tokenize(fitted_text))
        return set(emails_from_text)

    def find_emails_from_links(self, elements):
        """Return emails present in links"""
        emails_from_urls = map(self.parse_url, elements)
        return set(emails_from_urls)
