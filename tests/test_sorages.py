from unittest import TestCase, IsolatedAsyncioTestCase

from kryptone.conf import settings
from kryptone.storages import FileStorage


class TestFileStorage(TestCase):
    @classmethod
    def setUpClass(cls):
        media_path = settings.GLOBAL_KRYPTONE_PATH.parent.joinpath(
            'tests',
            'testproject',
            'media'
        )
        cls.instance = FileStorage(storage_path=media_path)
        cls.instance.initialize()

    def test_global_function(self):
        self.assertIn('performance.json', self.instance.storage)

    def test_get_file(self):
        file = self.instance.get_file('performance.json')
        self.assertTrue('performance.json' == file)

    def test_read_file(self):
        data = self.instance.read_file('performance.json')
        self.assertIn('days', data)

    def test_save_file(self):
        data = self.instance.read_file('performance.json')
        data['days'] = 1
        self.instance.save('performance.json', data)
