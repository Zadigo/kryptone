from unittest import IsolatedAsyncioTestCase, TestCase

from kryptone.conf import settings
from kryptone.storages import FileStorage, File


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
        self.assertIn('days', data)

    async def test_save_file(self):
        file = await self.instance.get_file('performance.json')
        data = await file.read()
        data['days'] = 1
        await self.instance.save('performance.json', data)
