from multiprocessing import Process
import os
import re
import time
from collections import Counter, defaultdict
from urllib.parse import urlparse

import requests
from lxml import etree
from nltk.tokenize import NLTKWordTokenizer
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sklearn.feature_extraction.text import CountVectorizer
from utils import read_json_document, write_json_document

from kryptone.kryptone import cache, logger


class TextMixin:
    tokenizer_class = NLTKWordTokenizer

    @staticmethod
    def get_text_length(text):
        """Get the length of the
        incoming text"""
        return len(text)
    
    def tokenize(self, text):
        """Create word tokens from a text"""
        instance = self.tokenizer_class()
        return instance.tokenize(text)

    def get_vectorizer(self, language='en'):
        """Vectorize a document"""
        filename = 'stop_words_french' if language == 'fr' else 'stop_words_english'
        # text = storage.get_file_content(filename)

        # tokenizer = LineTokenizer()
        # french_stop_words = tokenizer.tokenize(text)

        # return CountVectorizer(
        #     stop_words=french_stop_words,
        #     max_df=1.0
        # )


class SEOMixin(TextMixin):
    error_pages = set()

    @property
    def get_page_images(self):
        return self.driver.find_element(By.TAG_NAME, 'img')

    @property
    def get_page_title(self):
        element = self.driver.find_element(By.TAG_NAME, 'title')
        try:
            return element.text
        except:
            return ''
    
    @property
    def get_page_description(self):
        element = self.driver.find_element(
            By.CSS_SELECTOR,
            "meta[name='description']"
        )
        try:
            return element.text
        except:
            return ''
        
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
        element = self.driver.find_element(By.TAG_NAME, 'h1')
        return True if element else False
    
    @property
    def title_is_valid(self):
        return self.get_page_title <= 60
    
    @property
    def description_is_valid(self):
        return self.get_page_title <= 150
    
    @property
    def get_page_text(self):
        return self.driver.find_element(By.XPATH, '//body').text
        
    def most_common_words(self):
        counter = Counter(self.tokenize(self.get_page_text))
        most_common = counter.most_common(10)
        return most_common
    
    def get_page_status_code(self):
        pass
    
    def build_complete_page_audit(self, current_url):
        audit = {
            'title': self.get_page_title,
            'title_length': self.get_text_length(self.get_page_title),
            'title_is_valid': self.title_is_valid,
            'description': self.get_page_description,
            'description_length': self.get_text_length(self.get_page_description),
            'description_is_valid': self.description_is_valid,
            'url': current_url,
            'page_content_length': len(self.get_page_text),
            'word_count_analysis': dict(self.most_common_words()),
            'status_code': None
        }
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
        value = element.get_attibute('href')
        if value is not None and '@' in value:
            return value
        return None
    
    def parse_protected_email(self, email):
        pass 

    def emails(self):
        """Returns a set of valid email
        addresses on the current page"""
        def validate_values(value):
            if value is None:
                return False

            result = re.match(r'^(?:mailto\:)?(.*\@.*)$', value)
            if result:
                return True
        
        emails_from_text = self.find_emails_from_links('')
        emails_from_links = self.find_emails_from_text('')
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


class BaseCrawler(SEOMixin, EmailMixin):
    start_url = None
    urls_to_visit = set()
    visited_urls = set()
    url_validators = []
    url_filters = []

    def __init__(self):
        path = os.environ.get(
            'KAPIOPA_WEBDRIVER',
            'C:/Users/pendenquej\Downloads/chromedriver_win32/chromedriver.exe'
        )
        self._start_url_object = urlparse(self.start_url)
        self.driver = Chrome(executable_path=path)
        self.urls_to_visit.add(self.start_url)

    @property
    def get_html_page_content(self):
        return self.driver.page_source
    
    def run_validators(self, url):
        """Validates an url before it is
        included in the list of urls to visit"""
        results = []
        if self.url_validators:
            for validator in self.url_validators:
                if not callable(validator):
                    continue

                result = validator(url, driver=self.driver)
                if result is None:
                    result = False
                results.append(result)
            test_result = all(results)

            if test_result:
                message = f"Validation successful for {url}"
            else:
                message = f"Validation failed for {url}"
            logger.instance.info(message)
        return True
    
    def run_filters(self, exclude=True):
        """Filters out or in urls
        included in the list of urls to visit.
        The default action is to exclude all urls that
        meet specified conditions"""
        urls_to_filter = []
        for instance in self.url_filters:
            if not urls_to_filter:
                urls_to_filter = list(filter(instance, self.urls_to_visit))
            else:
                urls_to_filter = list(filter(instance, urls_to_filter))
        logger.instance.info(f"Filter runned on {len(self.urls_to_visit)} - {len(urls_to_filter)} urls remaining")
        return urls_to_filter
    
    def scroll_to(self, percentage=80):
        percentage = percentage / 100
        script = f"""
        const height = document.body.scrollHeight;
        const pixels = Math.round(height * {percentage});
        window.scrollTo(0, pixels);
        """
        self.driver.execute_script(script)

    def scroll_window(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def get_page_urls(self, same_domain=True):
        # current_page_urls = set()
        elements = self.driver.find_elements(By.TAG_NAME, 'a')
        for element in elements:
            link = element.get_attribute('href')
            link_object = urlparse(link)

            if link in self.urls_to_visit:
                continue

            if link in self.visited_urls:
                continue
            
            if link_object.netloc != self._start_url_object.netloc:
                continue
            
            # If the url contains a fragment, it's the same
            # as visiting the root element of that page
            # e.g. example.com/#google == example.com/
            if link_object.fragment:
                continue
            
            # If we already visited the home page then
            # skip all urls that include this home page
            if link_object.path == '/' and self._start_url_object.path == '/':
                continue
            
            # Reconstruct a partial url e.g. /google -> https://example.com/google
            if link_object.path != '/' and link.startswith('/'):
                link = f'{self._start_url_object.scheme}://{self._start_url_object.netloc}{link}'

            self.urls_to_visit.add(link)

        logger.instance.info(f"Found {len(elements)} urls")

    def run_actions(self, current_url, **kwargs):
        """Run additional actions of the currently
        visited web page"""

    def resume(self, **kwargs):
        """From a previous list of urls to visit and
        visited urls, resume web scrapping"""
        data = read_json_document('cache.json')
        self.urls_to_visit = data['urls_to_visit']
        self.visited_urls = data['visited_urls']
        self.start(**kwargs)

    def start_from_xml(self, url):
        if not url.endswith('.xml'):
            raise ValueError()
        
        response = requests.get(url)
        parser = etree.XMLParser(encoding='utf-8')
        xml = etree.fromstring(response.content, parser)

    def start(self, start_urls=[], wait_time=25):
        """Entrypoint to start the web scrapper"""
        logger.instance.info('Starting Kryptone...')
        if start_urls:
            self.urls_to_visit.update(set(start_urls))

        while self.urls_to_visit:
            current_url = self.urls_to_visit.pop()
            logger.instance.info(f"{len(self.urls_to_visit)} urls left to visit")

            current_url_object = urlparse(current_url)
            # If we are not the same domain as the start
            # url, stop, since we are not interested in
            # exploring the whole internet
            if current_url_object.netloc != self._start_url_object.netloc:
                continue

            self.driver.get(current_url)

            wait = WebDriverWait(self.driver, 5)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            
            self.visited_urls.add(current_url)

            self.get_page_urls()
            self.run_actions(current_url)

            urls_data = {
                'urls_to_visit': list(self.urls_to_visit),
                'visited_urls': list(self.visited_urls)
            }
            cache.set_value('urls_data', urls_data)

            write_json_document('cache.json', urls_data)

            logger.instance.info(f"Waiting {wait_time} seconds...")
            time.sleep(wait_time)


class Test(BaseCrawler):
    start_url = 'http://gency313.fr/'

    def run_actions(self, current_url, **kwargs):
        emails = self.find_emails_from_text(self.get_page_text)
        # print(emails)


if __name__ == '__main__':
    t = Test()
    t.start(wait_time=10)
    
    try:
        process = Process(target=t.start, kwargs={'wait_time': 10})
        process.start()
        process.join()
    except:
        process.close()
