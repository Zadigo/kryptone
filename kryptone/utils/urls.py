from kryptone import logger
from urllib.parse import urljoin, urlparse
from kryptone.utils.file_readers import read_document

import requests

from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.conf import settings


class URL:
    """Represents an url"""

    def __init__(self, url_string):
        self.raw_url = url_string
        self.url_object = urlparse(self.raw_url)

    @property
    def is_path(self):
        return self.raw_url.startswith('/')

    def __repr__(self):
        return f'<URL: {self.raw_url}>'

    def __str__(self):
        return self.raw_url

    def __eq__(self, obj):
        return self.raw_url == obj

    def __add__(self, obj):
        return urljoin(self.raw_url, obj)

    def __contains__(self, obj):
        return obj in self.raw_url

    def __hash__(self):
        return hash([self.raw_url])

    @property
    def is_valid(self):
        return self.raw_url.startswith('http')

    @property
    def has_fragment(self):
        return any([
            self.url_object.fragment != '',
            self.raw_url.endswith('#')
        ])

    def is_same_domain(self, url):
        incoming_url_object = urlparse(url)
        return incoming_url_object.netloc == self.url_object.netloc
    
    def get_status(self):
        headers = {
            'User-Agent': RANDOM_USER_AGENT()
        }
        response = requests.get(self.raw_url, headers=headers)
        return response.ok, response.status_code


class URLFile:
    urls = []
    def __init__(self, processor=None):
        try:
            data = read_document('urls.txt')
        except:
            logger.info('No urls were loaded from url cache file')
        else:
            urls = data.split('\n')
            if processor is not None:
                for url in urls:
                    self.urls.append(processor(url))

    def __iter__(self):
        return iter(self.urls)
    
    def __str__(self):
        return self.urls


