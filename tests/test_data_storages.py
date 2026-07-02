import csv
import json
import pathlib
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, PropertyMock


from kryptone.base import SiteCrawler
from kryptone.conf import settings
from kryptone.data_storages import File, FileStorage, GoogleSheetStorage, RedisStorage
from kryptone.utils.urls.managers import JSON_BACKUP_TEMPLATE
from kryptone.utils.urls.base import URL


class TestFileStorage(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_path: pathlib.Path = settings.GLOBAL_KRYPTONE_PATH.parent.joinpath(
            "tests", "testproject", "media"
        )

        # Create paths for seen_urls.csv and performance.json
        cls.seen_urls_path = cls.media_path.joinpath("seen_urls.csv")
        cls.performance_path = cls.media_path.joinpath("performance.json")

        mock_spider = MagicMock(spec=SiteCrawler)
        type(mock_spider).spider_uuid = PropertyMock(return_value="123")
        cls.mock_spider = mock_spider

        if not cls.media_path.exists():
            cls.media_path.mkdir()

            with cls.seen_urls_path.open(mode="w", newline="\n", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["urls"])

            with cls.performance_path.open(mode="w", encoding="utf-8") as f:
                json.dump(JSON_BACKUP_TEMPLATE, f)

        cls.instance = FileStorage(spider=mock_spider, storage_path=cls.media_path)
        cls.instance.initialize()

    @classmethod
    async def asyncTearDownClass(cls):
        files = cls.media_path.glob("**/*")
        for file in files:
            file.unlink()
        cls.media_path.rmdir()

    async def test_object(self):
        file = File(self.seen_urls_path)
        self.assertTrue(file.is_csv)
        self.assertTrue(file == "seen_urls.csv")

    async def test_storage_attribute(self):
        self.assertIsInstance(self.instance.storage, dict)
        self.assertIn("seen_urls.csv", self.instance.storage)

    async def test_get_file(self):
        file = await self.instance.get_file("seen_urls.csv")
        self.assertTrue("seen_urls.csv" == file)

    async def test_read_csv_file(self):
        file = await self.instance.get_file("seen_urls.csv")
        data = await file.read()
        self.assertIsInstance(data, list)
        self.assertIn("urls", data[0])

    async def test_save_file(self):
        file = await self.instance.get_file("performance.json")
        data = await file.read()
        data["duration"] = 1
        await self.instance.save("performance.json", data)

    async def test_csv_file(self):
        data = [["urls"], ["https://example.com"]]
        await self.instance.save("seen_urls.csv", data)

    async def test_has_file(self):
        self.assertTrue(await self.instance.has("seen_urls.csv"))

    async def test_get(self):
        data = await self.instance.get("performance.json")
        self.assertIsInstance(data, dict)
        self.assertIn("duration", data)


class TestRealtimeRedisStorage(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        mock_spider = MagicMock(spec=SiteCrawler)
        type(mock_spider).spider_uuid = PropertyMock(return_value="123")

        cls.storage = RedisStorage(spider=mock_spider)

    def test_connection(self):
        self.assertTrue(self.storage.is_connected)

    async def test_save_value(self):
        initial = {"a": 1, "b": 2}
        await self.storage.save("kryptone_test", initial)

        value = await self.storage.get("kryptone_test")
        self.assertDictEqual(
            initial, value, f"Saved and retrieved values do not match: {value}"
        )

        self.assertIsInstance(value, dict)

    async def test_before_save(self):
        testcases = [
            {"value": URL("https://example.com"), "expected": "https://example.com"},
            {
                "value": {"key": URL("https://example.com")},
                "expected": {"key": "https://example.com"},
            },
            {
                "value": [URL("https://example.com")],
                "expected": ["https://example.com"],
            },
            {
                "value": (URL("https://example.com"),),
                "expected": ["https://example.com"],
            },
        ]

        for testcase in testcases:
            with self.subTest(testcase=testcase):
                result = self.storage.before_save(testcase["value"])
                self.assertEqual(result, testcase["expected"])


class TestGoogleSheetStorage(IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        mock_spider = MagicMock(spec=SiteCrawler)
        type(mock_spider).spider_uuid = PropertyMock(return_value="123")

        cls.credentials_path: pathlib.Path = (
            settings.GLOBAL_KRYPTONE_PATH.parent.joinpath(
                "tests", "testproject", "credentials.json"
            )
        )
        settings["STORAGE_GOOGLE_SHEET_CREDENTIALS"] = cls.credentials_path
        cls.instance = GoogleSheetStorage(spider=mock_spider)

    async def test_connection(self):
        self.assertTrue(self.instance.is_connected)

    async def test_get_worksheet(self):
        sheet = await self.instance.get_worksheet("Sheet1")
        self.assertIsNotNone(sheet)
