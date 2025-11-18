import unittest
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

from kryptone.base import SiteCrawler
from kryptone.conf import settings
from kryptone.routing import Router, route


class TestSpider(SiteCrawler):
    class Meta:
        router = Router([
            route('/my_function', path='/'),
            route('other_function', regex='/1234')
        ])

    def my_function(self):
        pass

    def other_function(self):
        pass


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_project_path = pathlib.Path('./tests/testproject').absolute()

        settings['PROJECT_PATH'] = test_project_path
        settings['MEDIA_FOLDER'] = test_project_path / 'media'

        cls.spider = TestSpider()

        cls.p1 = patch('selenium.webdriver.Edge')
        cls.p2 = patch('kryptone.base.get_selenium_browser_instance')

        mocked_edge = cls.p1.start()
        mocked_selenium_instance = cls.p2.start()
        mocked_selenium_instance.return_value = mocked_edge

        mocked_storage = MagicMock()
        mocked_storage.initialize.return_value = None
        mocked_storage.save_or_create = AsyncMock()

        cls.spider.storage = mocked_storage

    @classmethod
    def tearDownClass(cls):
        cls.p1.stop()
        cls.p2.stop()

    def test_structure(self):
        self.spider.start()
