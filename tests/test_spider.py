import dataclasses
import pathlib
import unittest
import pathlib
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

from kryptone.data_storages import FileStorage
from kryptone.base import SiteCrawler
from kryptone.conf import settings
from kryptone.utils.urls import URL, URLIgnoreTest

VALID_URLS = [
    "http://www.example.com/",
    "HTTP://WWW.EXAMPLE.COM/",
    "http://localhost/",
    "http://example.com/",
    "http://example.com:0",
    "http://example.com:0/",
    "http://example.com:65535",
    "http://example.com:65535/",
    "http://example.com./",
    "http://www.example.com/",
    "http://www.example.com:8000/test",
    "http://valid-with-hyphens.com/",
    "http://subdomain.example.com/",
    "http://a.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "http://200.8.9.10/",
    "http://200.8.9.10:8000/test",
    "http://su--b.valid-----hyphens.com/",
    "http://example.com?something=value",
    "http://example.com/index.php?something=value&another=value2",
    "https://example.com/",
    "ftp://example.com/",
    "ftps://example.com/",
    "http://foo.com/blah_blah",
    "http://foo.com/blah_blah/",
    "http://foo.com/blah_blah_(wikipedia)",
    "http://foo.com/blah_blah_(wikipedia)_(again)",
    "http://www.example.com/wpstyle/?p=364",
    "https://www.example.com/foo/?bar=baz&inga=42&quux",
    "http://✪df.ws/123",
    "http://userid@example.com",
    "http://userid@example.com/",
    "http://userid@example.com:8080",
    "http://userid@example.com:8080/",
    "http://userid@example.com:65535",
    "http://userid@example.com:65535/",
    "http://userid:@example.com",
    "http://userid:@example.com/",
    "http://userid:@example.com:8080",
    "http://userid:@example.com:8080/",
    "http://userid:password@example.com",
    "http://userid:password@example.com/",
    "http://userid:password@example.com:8",
    "http://userid:password@example.com:8/",
    "http://userid:password@example.com:8080",
    "http://userid:password@example.com:8080/",
    "http://userid:password@example.com:65535",
    "http://userid:password@example.com:65535/",
    "https://userid:paaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaassword@example.com",
    "https://userid:paaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaassword@example.com:8080",
    "https://useridddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "dddddddddddddddddddddd:password@example.com",
    "https://useridddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    "ddddddddddddddddd:password@example.com:8080",
    "http://userid:password" + "d" * 2000 + "@example.aaaaaaaaaaaaa.com",
    "http://142.42.1.1/",
    "http://142.42.1.1:8080/",
    "http://➡.ws/䨹",
    "http://⌘.ws",
    "http://⌘.ws/",
    "http://foo.com/blah_(wikipedia)#cite-1",
    "http://foo.com/blah_(wikipedia)_blah#cite-1",
    "http://foo.com/unicode_(✪)_in_parens",
    "http://foo.com/(something)?after=parens",
    "http://☺.damowmow.com/",
    "http://djangoproject.com/events/#&product=browser",
    "http://j.mp",
    "ftp://foo.bar/baz",
    "http://foo.bar/?q=Test%20URL-encoded%20stuff",
    "http://مثال.إختبار",
    "http://例子.测试",
    "http://उदाहरण.परीक्षा",
    "http://-.~_!$&'()*+,;=%40:80%2f@example.com",
    "http://xn--7sbb4ac0ad0be6cf.xn--p1ai",
    "http://1337.net",
    "http://a.b-c.de",
    "http://223.255.255.254",
    "ftps://foo.bar/",
    "http://10.1.1.254",
    "http://[FEDC:BA98:7654:3210:FEDC:BA98:7654:3210]:80/index.html",
    "http://[::192.9.5.5]/ipng",
    "http://[::ffff:192.9.5.5]/ipng",
    "http://[::1]:8080/",
    "http://0.0.0.0/",
    "http://255.255.255.255",
    "http://224.0.0.0",
    "http://224.1.1.1",
    "http://111.112.113.114/",
    "http://88.88.88.88/",
    "http://11.12.13.14/",
    "http://10.20.30.40/",
    "http://1.2.3.4/",
    "http://127.0.01.09.home.lan",
    "http://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.ex"
    "ample.com",
    "http://example.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaa.com",
    "http://example.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "http://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaa"
    "aaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "http://dashintld.c-m",
    "http://multipledashintld.a-b-c",
    "http://evenmoredashintld.a---c",
    "http://dashinpunytld.xn---c",
]

INVALID_URLS = [
    None,
    56,
    "no_scheme",
    "foo",
    "http://",
    "http://example",
    "http://example.",
    "http://example.com:-1",
    "http://example.com:-1/",
    "http://example.com:000000080",
    "http://example.com:000000080/",
    "http://.com",
    "http://invalid-.com",
    "http://-invalid.com",
    "http://invalid.com-",
    "http://invalid.-com",
    "http://inv-.alid-.com",
    "http://inv-.-alid.com",
    "file://localhost/path",
    "git://example.com/",
    "http://.",
    "http://..",
    "http://../",
    "http://?",
    "http://??",
    "http://??/",
    "http://#",
    "http://##",
    "http://##/",
    "http://foo.bar?q=Spaces should be encoded",
    "//",
    "//a",
    "///a",
    "///",
    "http:///a",
    "foo.com",
    "rdar://1234",
    "h://test",
    "http:// shouldfail.com",
    ":// should fail",
    "http://foo.bar/foo(bar)baz quux",
    "http://-error-.invalid/",
    "http://dashinpunytld.trailingdot.xn--.",
    "http://dashinpunytld.xn---",
    "http://-a.b.co",
    "http://a.b-.co",
    "http://a.-b.co",
    "http://a.b-.c.co",
    "http:/",
    "http://",
    "http://",
    "http://1.1.1.1.1",
    "http://123.123.123",
    "http://3628126748",
    "http://123",
    "http://000.000.000.000",
    "http://016.016.016.016",
    "http://192.168.000.001",
    "http://01.2.3.4",
    "http://01.2.3.4",
    "http://1.02.3.4",
    "http://1.2.03.4",
    "http://1.2.3.04",
    "http://.www.foo.bar/",
    "http://.www.foo.bar./",
    "http://[::1:2::3]:8/",
    "http://[::1:2::3]:8080/",
    "http://[]",
    "http://[]:8080",
    "http://example..com/",
    "http://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.e"
    "xample.com",
    "http://example.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaa.com",
    "http://example.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    "aaaaaa",
    "http://example." + ("a" * 63 + ".") * 1000 + "com",
    "http://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaa."
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaa"
    "aaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaa"
    "aaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaaaaaaaaa",
    "https://test.[com",
    "http://@example.com",
    "http://:@example.com",
    "http://:bar@example.com",
    "http://foo@bar@example.com",
    "http://foo/bar@example.com",
    "http://foo:bar:baz@example.com",
    "http://foo:bar@baz@example.com",
    "http://foo:bar/baz@example.com",
    "http://invalid-.com/?m=foo@example.com",
    # Newlines and tabs are not accepted.
    "http://www.djangoproject.com/\n",
    "http://[::ffff:192.9.5.5]\n",
    "http://www.djangoproject.com/\r",
    "http://[::ffff:192.9.5.5]\r",
    "http://www.django\rproject.com/",
    "http://[::\rffff:192.9.5.5]",
    "http://\twww.djangoproject.com/",
    "http://\t[::ffff:192.9.5.5]",
    # Trailing junk does not take forever to reject.
    "http://www.asdasdasdasdsadfm.com.br ",
    "http://www.asdasdasdasdsadfm.com.br z"
]


class SpiderMixin:
    @classmethod
    def setUpClass(cls):
        test_project_path = pathlib.Path('./tests/testproject').absolute()

        settings['PROJECT_PATH'] = test_project_path
        settings['MEDIA_FOLDER'] = test_project_path / 'media'

        cls.p1 = patch('selenium.webdriver.Edge')
        cls.p2 = patch('kryptone.base.get_selenium_browser_instance')

        mocked_edge = cls.p1.start()
        mocked_selenium_instance = cls.p2.start()

        mocked_edge.get.return_value = URL('http://example.com')
        mocked_edge.maximize_window.return_value = True

        # Return a mock of the Selenium Webdriver
        mocked_selenium_instance.return_value = mocked_edge

        # Mock url retrieval on a given page
        mocked_selenium_instance.execute_script.return_value = [
            'http://example.com/1',
            'http://example.com/2'
        ]

        # Return a mock storage
        mocked_storage = MagicMock()
        mocked_storage.initialize.return_value = None
        mocked_storage.save_or_create = AsyncMock()

        cls.spider = SiteCrawler()
        cls.spider.storage = mocked_storage
        cls.start_urls = ['https://example.com']

        mocked_selenium_instance.assert_called_once_with(
            browser_name=None,
            headless=False,
            load_images=True,
            load_js=True
        )

        cls.mocked_edge = mocked_edge

        # # TODO: Reunite these two functions
        # # into one single efficient one
        # cls.spider.setup_class()
        # cls.spider.before_start([])


class TestSpider(SpiderMixin, unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        cls.p1.stop()
        cls.p2.stop()

    # @patch('data_storages.FileStorage', autospec=FileStorage, new_callable=AsyncMock)
    def test_structure(self):
        self.spider.start(self.start_urls)
        self.mocked_edge.get.assert_called_once_with(self.start_urls[0])

        self.assertTrue(
            hasattr(self.spider, '_meta'),
            'Spider has no _meta attribute'
        )

        crawl = getattr(self.spider._meta, 'crawl')
        self.assertTrue(crawl, 'Spider has no crawl attribute set to True')

    @patch.object(SiteCrawler, 'collect_page_urls')
    @patch.object(URL, 'is_same_domain', return_value=True)
    def test_collect_page_urls(self, mock_collect_page_urls, mock_is_same_domain):
        mock_collect_page_urls.return_value = VALID_URLS + INVALID_URLS
        urls = self.spider.collect_page_urls()
        self.spider.start_url = URL('http://example.com/')
        self.spider.add_urls(urls)

        for url in self.spider.urls_to_visit:
            with self.subTest(url=url):
                self.assertNotIn(url, INVALID_URLS)

    def test_url_collection_with_different_domains(self):
        urls = [
            URL('http://example.com/product-1'),
            URL('http://ecommerce.com/product-1')
        ]

        self.spider.start_url = urls[0]
        self.spider.add_urls(urls)
        
        self.assertTrue(
            len(self.spider.urls_to_visit) > 0, 
            'No URLs were collected'
        )
        
        self.assertIn(
            urls[0], 
            self.spider.urls_to_visit,
            'URL from same domain was not collected'
        )

    def test_collect_page_urls_with_url_gather_ignore_tests(self):
        collected_urls = [
            URL('http://example.com/product-1'),
            URL('http://example.com/product-2'),
            URL('http://example.com/2')
        ]

        self.spider.start_url = URL('http://example.com/')
        self.spider._meta.url_gather_ignore_tests.append(r'/product-\d+')

        self.spider.add_urls(collected_urls)

        for url in self.spider.urls_to_visit:
            with self.subTest(url=url):
                self.assertIn(
                    url,
                    [URL('http://example.com/2')],
                    'Url should not have been selected'
                )

    def test_collect_page_urls_with_limit_to(self):
        pass

    def test_collect_page_urls_with_url_rule_tests(self):
        pass

    @patch('requests.get')
    def test_download_images(self, mock_get_request: Mock):
        test_urls = ['http://example.com/logos/img1.jpg']
        page_url = 'http://example.com'

        mock_response = MagicMock()

        with open(pathlib.Path('.').absolute().joinpath('tests/data/img1.jpg'), 'rb') as f:
            type(mock_response).content = PropertyMock(return_value=f.read())
        type(mock_response).status_code = PropertyMock(return_value=200)

        mock_get_request.return_value = mock_response

        path = pathlib.Path('.').absolute().joinpath('tests/data')
        self.spider.download_images(test_urls, page_url, directory=path)
        # mock_get_request.assert_called_with()

    def test_save_object(self):
        @dataclasses.dataclass
        class TestModel:
            name: str = None

        self.spider.model = TestModel
        self.spider.save_object({'name': 'Kendall Jenner'})
        self.assertTrue(len(self.spider.DATA_CONTAINER) > 0)

    def test_backup_urls(self):
        self.spider.backup_urls()


class TestWithIgnores(SpiderMixin, unittest.TestCase):
    def test_collect_page_urls_with_url_ignore_tests(self):
        collected_urls = [
            URL('http://example.com/product-1'),
            URL('http://example.com/product-2'),
            URL('http://example.com/2')
        ]

        self.spider._meta.url_ignore_tests.append(
            URLIgnoreTest('base', paths=['/2'])
        )

        self.spider.add_urls(collected_urls)

        for url in self.spider.urls_to_visit:
            with self.subTest(url=url):
                self.assertNotIn(collected_urls[-1], self.spider.urls_to_visit)
