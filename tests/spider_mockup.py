import datetime
import json
import random
import re
import string
import time
from collections import defaultdict, namedtuple
from urllib.parse import unquote, urlparse, urlunparse

import pytz
import requests
from lxml import etree
from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from kryptone import logger
from kryptone.conf import settings
from kryptone.mixins import EmailMixin, SEOMixin
from kryptone.signals import Signal
from kryptone.utils.file_readers import (read_json_document,
                                         write_csv_document,
                                         write_json_document)
from kryptone.utils.iterators import JPEGImagesIterator
from kryptone.utils.randomizers import RANDOM_USER_AGENT
from kryptone.utils.urls import URL, URLFile, URLPassesTest


def run_filters(urls):
    tests = [
        URLPassesTest('/google')
    ]
    if tests:
        results = defaultdict(list)
        for url in urls:
            truth_array = results[url]
            for instance in tests:
                truth_array.append(instance(url))

        filtered_urls = []
        for url, truth_array in results.items():
            if not all(truth_array):
                continue
            filtered_urls.append(url)
        message = f"Url filter completed"
        logger.info(message)
        return filtered_urls
    # Ensure that we return the original
    # urls to visit if there are no filters
    # or this might return nothing
    return urls


def get_page_urls():
    urls = ['http://example.com', 'http://example.com/google']
    return run_filters(urls)


def post_navigation_actions(**kwargs):
    pass


def start_from_sitemap_xml(url):
    pass


def _backup_urls(urls_to_visit, visited_urls):
    urls_data = {
        'spider': 'Mockup',
        'timestamp': '',
        'urls_to_visit': list(urls_to_visit),
        'visited_urls': list(visited_urls)
    }

    write_json_document(
        f'{settings.CACHE_FILE_NAME}.json',
        urls_data
    )


def run_actions(current_url):
    pass


def start(start_urls=[], url_cache=None, **kwargs):
    start_xml_url = None
    start_url = 'http://example.com'
    _start_url_object = None
    urls_to_visit = set()
    visited_urls = set()

    logger.info(f'Ready to crawl website')

    wait_time = 10

    if True:
        logger.info('Starting Kryptone in debug mode...')
    else:
        logger.info('Starting Kryptone...')

    if url_cache is not None:
        urls_to_visit = url_cache.urls_to_visit
        visited_urls = url_cache.visited_urls

    if start_xml_url is not None:
        start_urls = start_from_sitemap_xml(start_xml_url)
    elif start_url is not None:
        urls_to_visit.add(start_url)
        _start_url_object = urlparse(start_url)

    if start_urls:
        urls_to_visit.update(start_url)

    while urls_to_visit:
        current_url = urls_to_visit.pop()
        logger.info(f"{len(urls_to_visit)} urls left to visit")

        if current_url is None:
            continue

        # In the case where the user has provided a
        # set of urls directly in the function,
        # start_url would be None
        if start_url is None:
            start_url = current_url
            _start_url_object = urlparse(start_url)

        current_url_object = urlparse(current_url)
        # If we are not on the same domain as the
        # starting url: *stop*. we are not interested
        # in exploring the whole internet
        if current_url_object.netloc != _start_url_object.netloc:
            continue

        logger.info(f'Going to url: {current_url}')

        # Always wait for the body section of
        # the page to be located  or visible
        post_navigation_actions(current_url=current_url)

        # Post navigation signal
        # TEST: This has to be tested
        # navigation.send(
        #     self,
        #     current_url=current_url,
        #     images_list_filter=['jpg', 'jpeg', 'webp']
        # )

        visited_urls.add(current_url)

        # We can either crawl all the website
        # or just specific page
        urls_to_visit = set(get_page_urls())
        _backup_urls(urls_to_visit, visited_urls)

        # Run custom user actions once
        # everything is completed
        url_instance = URL(current_url)
        run_actions(url_instance)

        if settings.WAIT_TIME_RANGE:
            start = settings.WAIT_TIME_RANGE[0]
            stop = settings.WAIT_TIME_RANGE[1]
            wait_time = random.randrange(start, stop)

        logger.info(f"Waiting {wait_time}s")
        time.sleep(wait_time)
