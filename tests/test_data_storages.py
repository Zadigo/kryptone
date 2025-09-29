import csv
import pathlib
from unittest import IsolatedAsyncioTestCase
from unittest import mock
from unittest.mock import MagicMock, Mock, PropertyMock, patch
from urllib.parse import urljoin
from uuid import uuid4

from selenium.webdriver import Edge

from kryptone.base import SiteCrawler
from kryptone.conf import settings
from kryptone.data_storages import (BaseStorage, File, FileStorage,
                                    GoogleSheetStorage, PostGresStorage,
                                    RedisStorage)
from kryptone.utils.urls import URL


class TestBaseStorage(IsolatedAsyncioTestCase):
    def setUp(self):
        self.instance = BaseStorage()

    def test_structure(self):
        self.instance.spider


class TestFileStorage(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_path: pathlib.Path = settings.GLOBAL_KRYPTONE_PATH.parent.joinpath(
            'tests',
            'testproject',
            'media'
        )

        cls.seen_urls_path = cls.media_path.joinpath('seen_urls.csv')
        cls.performance_path = cls.media_path.joinpath('performance.json')

        mock_spider = MagicMock(spec=SiteCrawler)
        type(mock_spider).spider_uuid = PropertyMock(return_result='123')
        cls.mock_spider = mock_spider

        if not cls.media_path.exists():
            cls.media_path.mkdir()

            with open(cls.seen_urls_path, mode='w') as f:
                writer = csv.writer(f)
                writer.writerow(['urls'])

        cls.instance = FileStorage(
            spider=mock_spider,
            storage_path=cls.media_path
        )
        cls.instance.initialize()

    async def asyncTearDown(self):
        files = self.media_path.glob('**/*')
        for file in files:
            file.unlink()
        self.media_path.rmdir()

    async def test_object(self):
        file = File(self.seen_urls_path)
        self.assertTrue(file.is_csv)
        self.assertTrue(file == 'seen_urls.csv')

    async def test_global_function(self):
        self.assertIn('performance.json', self.instance.storage)

    async def test_get_file(self):
        file = await self.instance.get_file('performance.json')
        self.assertTrue('performance.json' == file)

    async def test_read_file(self):
        file = await self.instance.get_file('performance.json')
        data = await file.read()
        self.assertIn('duration', data)

    async def test_save_file(self):
        file = await self.instance.get_file('performance.json')
        data = await file.read()
        data['duration'] = 1
        await self.instance.save('performance.json', data)


class TestRedisStorage(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        settings['STORAGE_REDIS_PASSWORD'] = 'django-local-testing'

        mock_spider = MagicMock(spec=SiteCrawler)
        type(mock_spider).spider_uuid = PropertyMock(return_result='123')
        cls.spider = mock_spider

        cls.connection = RedisStorage(spider=cls.spider)

    # def setUp(self):
    #     self.spider = None
    #     self.connection = None
    #     self.test_redis()

    # @patch('kryptone.base.get_selenium_browser_instance')
    # @patch('kryptone.base.SiteCrawler')
    # @patch('redis.Redis')
    # def test_redis(self, mock_func, mock_site_crawler: MagicMock, mock_redis: MagicMock):
    #     spider = mock_site_crawler.return_value
    #     spider.spider_uuid.return_value = uuid4()
    #     spider._meta.debug_mode.return_value = True
    #     self.spider = SiteCrawler()

    #     client = mock_redis.return_value
    #     client.hget.return_value = {'a': 1 }

    #     result = client.hget('key')
    #     self.assertDictEqual(result, {'a': 1 })

    async def test_connection(self):
        self.assertTrue(self.connection.is_connected)

    async def test_check_has_key(self):
        await self.connection.has('performance.json')

    async def test_save(self):
        result = await self.connection.save('kryptone_tests', 1)
        self.assertEqual(result, 1)

        expected = {'a': 1}
        await self.connection.save('kryptone_tests', expected)
        data = await self.connection.get('kryptone_tests')
        self.assertDictEqual(data, expected)

    async def test_saving_cache(self):
        cache = {
            'spider': 'ExampleSpider',
            'spider_uuid': self.spider.spider_uuid,
            'timestamp': '2024-45-29 14:45:23',
            'urls_to_visit': [],
            'visited_urls': [
                'http://example.com'
            ]
        }
        await self.connection.save(settings.CACHE_FILE_NAME, cache)
        await self.connection.save('seen_urls.csv', ['http://example.com'])

        result = await self.connection.get(settings.CACHE_FILE_NAME)
        self.assertEqual(result['spider_uuid'], str(cache['spider_uuid']))


# class TestApiStorage(IsolatedAsyncioTestCase):
#     @classmethod
#     def setUpClass(cls):
#         base_url = 'http://127.0.0.1:5000/api/v1/'

#         settings['STORAGE_API_GET_ENDPOINT'] = urljoin(base_url, 'seen-urls')
#         settings['STORAGE_API_SAVE_ENDPOINT'] = urljoin(base_url, 'save')

#         spider = MockupSpider()
#         cls.instance = ApiStorage(spider=spider)
#         cls.example_cache = {
#             'spider': 'ExampleSpider',
#             'spider_uuid': '739f3877-f67f-41ec-a940-3c1fbf2e3e53',
#             'timestamp': '2024-45-29 14:45:23',
#             'urls_to_visit': [],
#             'visited_urls': [
#                 'http://example.com'
#             ]
#         }

#     async def test_structure(self):
#         await self.instance.get('some_value')

#     async def test_invalid_key(self):
#         result = await self.instance.get('some_value')
#         self.assertFalse(result)

#     async def test_getting_cache(self):
#         result = await self.instance.get('cache')
#         self.assertIn('spider', result)
#         self.assertIn('urls_to_visit', result)

#     async def test_save(self):
#         result = await self.instance.save('cache', self.example_cache)
#         self.assertDictEqual(result, {'state': True})


class TestPostgreSQLStorage(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        settings['STORAGE_POSTGRESQL_DB_NAME'] = 'kryptone'
        settings['STORAGE_POSTGRESQL_USER'] = 'kryptone'
        settings['STORAGE_POSTGRESQL_PASSWORD'] = 'kryptone'
        settings['STORAGE_POSTGRESQL_HOST'] = 'localhost'
        cls.settings = settings
        cls.instance = PostGresStorage(spider=MockupSpider())

    def test_connection(self):
        self.assertTrue(self.instance.is_connected)
        self.instance.storage_connection.close()

    def test_insert_sql(self):
        values = [URL('http://example.com'), URL('http://example.com/1')]
        sql = self.instance.insert_sql('url_cache', *values)


class TestGoogleSheetStorage(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        mock_spider = MagicMock(spec=SiteCrawler)
        type(mock_spider).spider_uuid = PropertyMock(return_value='123')

        cls.credentials_path: pathlib.Path = settings.GLOBAL_KRYPTONE_PATH.parent.joinpath(
            'tests',
            'testproject',
            'credentials.json'
        )
        settings['STORAGE_GOOGLE_SHEET_CREDENTIALS'] = cls.credentials_path
        cls.instance = GoogleSheetStorage(spider=mock_spider)

    async def test_connection(self):
        self.assertTrue(self.instance.is_connected)

    async def test_get_worksheet(self):
        sheet = await self.instance.get_worksheet('Sheet1')
        self.assertIsNotNone(sheet)
