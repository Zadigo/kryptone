from unittest import IsolatedAsyncioTestCase
from urllib.parse import urljoin
from uuid import uuid4

from kryptone.conf import settings
from kryptone.data_storages import (ApiStorage, BaseStorage, File, FileStorage,
                                    RedisStorage)


class MockupSpider:
    def __init__(self):
        self.spider_uuid = uuid4()


class TestBaseStorage(IsolatedAsyncioTestCase):
    def setUp(self):
        self.instance = BaseStorage()

    def test_structure(self):
        self.instance.spider


class TestFileStorage(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_path = settings.GLOBAL_KRYPTONE_PATH.parent.joinpath(
            'tests',
            'testproject',
            'media'
        )
        cls.instance = FileStorage(storage_path=cls.media_path)
        cls.instance.initialize()

    def test_object(self):
        file = File(self.media_path.joinpath('seen_urls.csv'))
        self.assertTrue(file.is_csv)
        self.assertTrue(file == 'seen_urls.csv')

    def test_global_function(self):
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
        spider = MockupSpider()
        connection = RedisStorage(spider=spider)
        cls.connection = connection

    async def test_connection(self):
        self.assertTrue(self.connection.is_connected)

    async def test_check_has_key(self):
        self.connection.has('performance.json')

    async def test_save(self):
        result = await self.connection.save('kryptone_tests', 1)
        self.assertEqual(result, 1)

        expected = {'a': 1}
        await self.connection.save('kryptone_tests', expected)
        data = await self.connection.get('kryptone_tests')
        self.assertDictEqual(data, expected)


class TestApiStorage(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        base_url = 'http://127.0.0.1:5000/api/v1/'

        settings['STORAGE_API_GET_ENDPOINT'] = urljoin(base_url, 'seen-urls')
        settings['STORAGE_API_SAVE_ENDPOINT'] = urljoin(base_url, 'save')

        spider = MockupSpider()
        cls.instance = ApiStorage(spider=spider)
        cls.example_cache = {
            'spider': 'ExampleSpider',
            'spider_uuid': '739f3877-f67f-41ec-a940-3c1fbf2e3e53',
            'timestamp': '2024-45-29 14:45:23',
            'urls_to_visit': [],
            'visited_urls': [
                'http://example.com'
            ]
        }

    async def test_structure(self):
        await self.instance.get('some_value')

    async def test_invalid_key(self):
        result = await self.instance.get('some_value')
        self.assertFalse(result)

    async def test_getting_cache(self):
        result = await self.instance.get('cache')
        self.assertIn('spider', result)
        self.assertIn('urls_to_visit', result)

    async def test_save(self):
        result = await self.instance.save('cache', self.example_cache)
        self.assertDictEqual(result, {'state': True})
