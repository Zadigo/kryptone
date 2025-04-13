from sklearn.feature_extraction.text import TfidfVectorizer
from math import log
from collections import Counter
import pandas as pd
import numpy as np
import asyncio
import json
import re
import unicodedata
from collections import Counter, defaultdict, deque
from functools import cached_property

import kagglehub
import pandas
import requests
from bs4 import BeautifulSoup
from kagglehub import KaggleDatasetAdapter
from matplotlib import pyplot
from nltk.corpus import stopwords

from kryptone.conf import settings
from kryptone.utils.date_functions import get_current_date
from kryptone.utils.file_readers import read_document
from kryptone.utils.functions import create_filename
from kryptone.utils.iterators import keep_while
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.text import clean_text, remove_punctuation, slugify

EMAIL_REGEX = r'\S+\@\S+'


def long_text_processor(tokens):
    for token in tokens:
        if len(token) <= 30:
            return True
        return False


class TFIDFProcessor:
    """A class to calculate TF-IDF scores for documents and provide various
    utilities for text processing based on these scores"""

    def __init__(self, documents=None):
        self.documents = documents or []
        self.vocabulary = set()
        self.idf_values = {}
        self.tfidf_matrix = None
        self.feature_names = []

    def add_documents(self, documents):
        """Add documents to the collection"""
        if isinstance(documents, str):
            self.documents.append(documents)
        else:
            self.documents.extend(documents)

    def _calculate_tf(self, document):
        """Calculate term frequencies for 
        a single document"""
        if isinstance(document, str):
            tokens = document.lower().split()
        else:
            tokens = [t.lower() for t in document]

        # Count the occurrences of each token
        term_counts = Counter(tokens)
        total_terms = len(tokens)

        tf_dict = {
            term: count/total_terms for term,
                count in term_counts.items()
        }
        return tf_dict

    def _calculate_idf(self):
        """Calculate inverse document frequency for 
        all terms in the vocabulary"""
        # Count the number of documents 
        # that contain each term
        n_documents = len(self.documents)
        document_frequency = Counter()

        for document in self.documents:
            if isinstance(document, str):
                # If it's a string, tokenize and make
                #  a set of unique tokens
                unique_terms = set(document.lower().split())
            else:
                # If it's already tokenized, just make a set of unique tokens
                unique_terms = set(t.lower() for t in document)

            # Update the document frequency counter
            for term in unique_terms:
                document_frequency[term] += 1
                self.vocabulary.add(term)

        # Calculate IDF for each term
        self.idf_values = {
            term: log(n_documents / (1 + freq)) 
                for term, freq in document_frequency.items()
        }

        return self.idf_values

    def compute_tfidf(self):
        """Compute TF-IDF scores for all documents"""
        # Ensure IDF values are calculated
        if not self.idf_values:
            self._calculate_idf()

        # Compute TF-IDF for each document
        tfidf_documents = []

        for document in self.documents:
            tf_values = self._calculate_tf(document)
            tfidf_dict = {
                term: tf * self.idf_values.get(term, 0)
                for term, tf in tf_values.items()
            }
            tfidf_documents.append(tfidf_dict)

        return tfidf_documents

    def compute_tfidf_matrix(self):
        """Compute the TF-IDF matrix using scikit-learn"""
        vectorizer = TfidfVectorizer()
        self.tfidf_matrix = vectorizer.fit_transform(self.documents)
        self.feature_names = vectorizer.get_feature_names_out()
        return self.tfidf_matrix

    def filter_tokens_by_tfidf(self, document_idx, top_n=None, threshold=None):
        """
        Filter tokens in a document based on their TF-IDF scores
        
        Args:
            document_idx: Index of the document in the collection
            top_n: Keep only the top N tokens by TF-IDF score
            threshold: Keep only tokens with TF-IDF score above this threshold
        """
        # Ensure TF-IDF matrix is computed
        if self.tfidf_matrix is None:
            self.compute_tfidf_matrix()

        # Get the TF-IDF scores for the specified document
        tfidf_scores = self.tfidf_matrix[document_idx].toarray()[0]

        # Create a dictionary mapping terms 
        # to their TF-IDF scores
        term_scores = {
            self.feature_names[i]: score
                for i, score in enumerate(tfidf_scores)
                    if score > 0  # Only include terms that actually appear in the document
        }

        # Filter tokens based on parameters
        if threshold is not None:
            filtered_terms = {
                term: score for term, score in term_scores.items()
                if score >= threshold
            }
        elif top_n is not None:
            filtered_terms = dict(
                sorted(term_scores.items(),
                       key=lambda x: x[1], reverse=True)[:top_n]
            )
        else:
            # Default to returning all terms with their scores
            filtered_terms = term_scores

        # Return the document with only the filtered terms
        if isinstance(self.documents[document_idx], str):
            tokens = self.documents[document_idx].lower().split()
        else:
            tokens = [t.lower() for t in self.documents[document_idx]]

        return [token for token in tokens if token in filtered_terms]

    def get_top_terms(self, document_idx, n=10):
        """
        Get the top N terms for a document based on TF-IDF scores.
        
        Args:
            document_idx: Index of the document in the collection
            n: Number of top terms to return
            
        Returns:
            A list of (term, score) tuples sorted by decreasing score
        """
        # Ensure TF-IDF matrix is computed
        if self.tfidf_matrix is None:
            self.compute_tfidf_matrix()

        # Get the TF-IDF scores for the specified document
        tfidf_scores = self.tfidf_matrix[document_idx].toarray()[0]

        # Create a list of (term, score) tuples
        term_scores = [
            (self.feature_names[i], score)
            for i, score in enumerate(tfidf_scores)
            if score > 0  # Only include terms that actually appear in the document
        ]

        # Sort by decreasing score and return the top N
        return sorted(term_scores, key=lambda x: x[1], reverse=True)[:n]

    def preprocess_text_with_tfidf(self, keep_top_n=None, min_tfidf=None):
        """
        Process all documents by filtering tokens based on TF-IDF scores.
        
        Args:
            keep_top_n: Keep only the top N tokens by TF-IDF score in each document
            min_tfidf: Keep only tokens with TF-IDF score above this threshold
            
        Returns:
            A list of processed documents (as lists of tokens)
        """
        processed_documents = []
        for i in range(len(self.documents)):
            filtered_tokens = self.filter_tokens_by_tfidf(
                i, 
                top_n=keep_top_n, 
                threshold=min_tfidf
            )
            processed_documents.append(filtered_tokens)

        return processed_documents


class TextMixin:
    nltk_downloads = False
    text_processsors = [long_text_processor]

    def get_page_text(self):
        """Returns a raw extraction of
        the document's text"""
        script = """return document.body.outerHTML"""
        html_content = self.driver.execute_script(script)
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove all script tags from the body
        for tag in soup.find_all('script'):
            tag.extract()

        return soup.text

    def run_processors(self, tokens):
        result = []
        for processor in self.text_processors:
            if not callable(processor):
                continue
            if result:
                result = list(filter(processor, result))
            else:
                result = list(filter(processor, tokens))
        return result

    def fit_transform(self, text, language='english', keep_emails=False):
        """Fit transform tokenizes the text and removes all stop
        words. This function does structural destrctive changes to 
        the oringal text. The text is then run through the text processors"""
        import nltk
        from nltk.tokenize import word_tokenize

        abbreviations = None

        if not self.nltk_downloads:
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('wordnet')
            nltk.download('punkt_tab')
            nltk.download('omw-1.4')

            path = kagglehub.dataset_download('johnpendenque/french-abbreviations')
            abbreviations = pandas.read_csv(path)

            self.nltk_loaded = True

        text = self.fit(text, language=language, keep_emails=keep_emails)
        tokens = word_tokenize(text.lower(), language=language)

        french_stop_words = set(stopwords.words('french'))
        # The text might have english words so just in case
        # remove them from the orginal text
        english_stop_words = set(stopwords.words('english'))
        stop_words = french_stop_words.union(english_stop_words)

        # Final tokens
        clean_tokens = [token for token in tokens if token not in stop_words]

        common_words = self._get_common_words(clean_tokens, limit=10)

        return ' '.join(clean_tokens)

    def fit(self, raw_text, **kwargs):
        """"Fit the text by removing unwanted tokens,
        normalizing the text and removing punctuation"""
        if raw_text is None:
            return None

        keep_emails = kwargs.get('keep_emails', False)

        # Remove special formatting and markup
        # Remove references like (en), (d), etc.
        clean_text = re.sub(r'\([^)]*\)', '', raw_text)

        # Remove square brackets and their contents
        clean_text = re.sub(r'\[[^]]*\]', '', clean_text)

        # Handle unicode characters and accents
        clean_text = unicodedata.normalize('NFKD', clean_text)
        clean_text = clean_text.encode('ASCII', 'ignore').decode('utf-8')

        # Handle punctionation in the text - layer 1
        clean_text = remove_punctuation(
            clean_text, keep=['@'], email_exception=keep_emails)

        # Remove numbers and punctuation - layer 2
        clean_text = re.sub(r'[^\w\s]', ' ', clean_text)
        return clean_text


class SEOMixin(TextMixin):
    """A mixin for auditing a web page"""

    word_frequency_by_page = {}
    text_by_page = defaultdict(str)
    text_tokens_by_page = defaultdict(list)
    website_tokens = deque()
    stemmed_tokens = deque()
    page_audits = defaultdict(dict)
    website_word_frequency = {}

    @property
    def grouped_text(self):
        """Returns the body's text, description text
        and keyword text of an HTML document"""

    @property
    def get_page_description(self):
        script = """
        let el = document.querySelector('meta[name="description"]')
        return el && el.attributes.content.textContent
        """
        return self.driver.execute_script(script)

    @property
    def get_page_title(self):
        script = """
        let el = document.querySelector('title')
        return el && el.textContent
        """
        text = self.driver.execute_script(script)
        return self.fit(text)

    @property
    def get_page_keywords(self):
        script = """
        let el = document.querySelector('[name="keywords"]')
        return el && el.content || ''
        """
        text = self.driver.execute_script(script)
        return self.fit(self.validate_text(text))

    @cached_property
    def page_speed_script(self):
        path = settings.GLOBAL_KRYPTONE_PATH.joinpath(
            'data', 'js', 'page_speed.js'
        )
        with open(path, encoding='utf-8') as f:
            content = f.read()
        return content

    def create_word_cloud(self, frequency):
        from wordcloud import WordCloud

        page_title = self.get_page_title
        wordcloud = WordCloud()
        wordcloud.generate_from_frequencies(frequency)

        fig = pyplot.figure(figsize=[10, 10])
        pyplot.imshow(wordcloud)
        pyplot.axis('off')
        fig.savefig(f'{slugify(page_title)}')

    def create_graph(self, current_url, x_values, y_values):
        page_title = self.get_page_title
        fig = pyplot.figure()
        fig, axes = pyplot.subplots(figsize=[15, 6])
        axes.set_xlabel('Words')
        axes.set_ylabel('Count')
        axes.set_title(f"Words for {page_title}")
        axes.tick_params(which='major', width=1.00, length=5)
        # axes.text(20, 35, 'Some text')
        # axes.annotate('Something', xy=[30, 40], xytext=[14, 31], arrowprops={
        #               'facecolor': 'black', 'shrink': 0.05})
        # axes.set_xticks([0, 30, 70, 100])
        axes.legend()
        # axes.plot(x, y, 'o', label='words')
        axes.bar(x_values, y_values, color='b')
        fig.savefig(f'{slugify(page_title)}')

    def calculate_word_frequency(self, tokens):
        from nltk import FreqDist

        frequency = FreqDist(tokens)

        # Return only the values (text) for the
        # n-words which are most present in the
        # current document
        frequency_values = list(frequency.items())
        sorted_frequency = sorted(
            frequency_values,
            key=lambda x: x[1],
            reverse=True
        )[0:10]
        return frequency, sorted_frequency

    def create_stemmed_words(self, tokens):
        from nltk.stem import SnowballStemmer

        stemmer = SnowballStemmer('french')
        stemmed_words = [stemmer.stem(word=word) for word in tokens]
        self.stemmed_tokens.extendleft(stemmed_words)
        return stemmed_words

    def audit_structure(self, audit):
        """Audits the structural design of the page"""
        has_head_title = all([
            self.get_page_title is not None,
            self.get_page_title != ''
        ])
        audit['has_title'] = has_head_title

        # Check if the page has an H1 tag
        script = """
        const el = document.querySelector('h1')
        return el && el.textContent
        """
        result = self.driver.execute_script(script)
        audit['has_h1'] = False
        if result is not None:
            audit['has_h1'] = True
            audit['h1'] = clean_text(result)
        else:
            filename = create_filename(suffix='h1')

            screenshots_folder = settings.MEDIA_FOLDER / 'screenshots'
            if not screenshots_folder.exists():
                screenshots_folder.mkdir()

            path = screenshots_folder / filename
            self.driver.get_screenshot_as_file(path)

    def audit_head(self, audit):
        """Checks the head section of the
        given page"""
        page_title = self.get_page_title
        audit['title_is_valid'] = False
        if page_title is None:
            audit['title_length'] = len(page_title)
            audit['title_is_valid'] = len(page_title) <= 60

        page_description = self.get_page_description
        audit['description_is_valid'] = False
        if page_description is None:
            audit['description_length'] = len(page_description)
            audit['description_is_valid'] = len(page_description) <= 150

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

    def audit_page_speed(self, audit):
        result = self.driver.execute_script(self.page_speed_script)
        audit['timing'] = result

    def audit_page_status_code(self, current_url, audit):
        async def sender():
            headers = {'User-Agent': RANDOM_USER_AGENT()}
            try:
                response = requests.get(str(current_url), headers=headers)
            except:
                # If we get an error when trying to send
                # the request, just put status code 0
                audit['status_code'] = 0
            else:
                audit['status_code'] = response.status_code

        async def main():
            await sender()

        asyncio.run(main())

    def audit_page(self, current_url, generate_graph=False):
        raw_text = self.get_page_text()
        text, tokens = self.fit_transform(raw_text)
        self.website_tokens.extendleft(tokens)

        self.text_by_page[str(current_url)] = text
        self.text_tokens_by_page[str(current_url)] = tokens

        frequency, sorted_frequencies = self.calculate_word_frequency(tokens)
        self.word_frequency_by_page[str(current_url)] = dict(frequency)
        self.website_word_frequency.update(dict(frequency))

        if generate_graph:
            x_values = [x[0] for x in sorted_frequencies]
            y_values = [x[1] for x in sorted_frequencies]
            self.create_graph(current_url, x_values, y_values)

        audit = {
            'date': get_current_date(),
            'title': self.get_page_title,
            'description': self.get_page_description,
            'url': str(current_url),
            'page_content_length': len(self.get_page_text()),
            'is_https': current_url.is_secured,
        }

        self.audit_structure(audit)
        # self.audit_head(audit)
        # self.audit_structured_data(audit)
        # self.audit_images(audit)
        # self.audit_page_speed(audit)
        self.audit_page_status_code(current_url, audit)

        self.page_audits[str(current_url)] = audit
        return audit


class EmailMixin(TextMixin):
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

    def find_emails_from_text(self):
        """Return emails embedded in plain text"""
        text = self.fit_transform(self.get_page_text(), email_exception=True)
        emails_from_text = map(
            self.identify_email,
            text.split(' ')
        )
        return set(emails_from_text)

    def find_emails_from_links(self, elements):
        """Return emails present in links"""
        emails_from_urls = map(self.parse_url, elements)
        return set(emails_from_urls)
