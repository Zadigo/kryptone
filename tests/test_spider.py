from unittest.mock import MagicMock, Mock, patch
import pathlib
import unittest

from kryptone.base import SiteCrawler
from kryptone.conf import settings
from kryptone.utils.urls import URL, URLIgnoreRegexTest, URLIgnoreTest

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


class MySpider(SiteCrawler):
    class Meta:
        debug_mode = True
        start_urls = ['https://example.com']


class TestSpider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_project_path = pathlib.Path('./tests/testproject').absolute()

        settings['PROJECT_PATH'] = test_project_path
        settings['MEDIA_FOLDER'] = test_project_path / 'media'

        cls.spider = MySpider()
        # TODO: Reunite these two functions
        # into one single efficient one
        cls.spider.setup_class()
        cls.spider.before_start([])

    def test_structure(self):
        # In debug mode makes no sense to run
        # the spider since Selenium is not started
        self.assertFalse(self.spider.start())

    def test_get_urls(self):
        # We should get the start_url plus
        # the other urls that we were able
        # to get on the current page
        test_urls = {
            URL('https://example.com/product/1'),
            URL('https://example.com'),
            URL('http://example.com/product/2')
        }
        self.spider.add_urls(test_urls)
        self.assertSetEqual(
            self.spider.urls_to_visit,
            test_urls
        )

    def test_check_invalid_urls(self):
        objs = (URL(value) for value in INVALID_URLS)
        valid_urls = self.spider.check_urls(objs)
        print(valid_urls)
        # self.assertSetEqual(valid_urls, set())

    def test_check_valid_urls(self):
        result = self.spider.check_urls(VALID_URLS)
        self.assertEqual(len(result), len(VALID_URLS))

    def test_download_images(self):
        test_urls = [
            'https://static.bershka.net/assets/public/1174/9ac3/e8384037903b/afaee790a05e/00623152505-a3f/00623152505-a3f.jpg?ts=1717510394290&w=800',
            'https://static.bershka.net/assets/public/86b5/ec66/38704722bb2c/75f953f6182b/00623152505-p/00623152505-p.jpg?ts=1717510451241&w=800',
            'https://static.bershka.net/assets/public/1bb9/b521/03744fb982bc/8cff09929be0/00623152505-a1t/00623152505-a1t.jpg?ts=1717510385997&w=800'
        ]
        url = URL(
            'https://www.bershka.com/fr/robe-midi-bretelles-col-carr%C3%A9-c0p164869795.html?colorId=505'
        )
        self.spider.download_images(
            test_urls,
            url,
            filename_attrs={'suffix': 'some name'}
        )


class TestIgnoresSpider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        test_project_path = pathlib.Path('./tests/testproject').absolute()

        settings['PROJECT_PATH'] = test_project_path
        settings['MEDIA_FOLDER'] = test_project_path / 'media'

        cls.spider = MySpider()
        cls.spider.setup_class()
        cls.spider.before_start([])

    def test_url_ignore_test(self):
        self.spider._meta.url_ignore_tests.append(
            URLIgnoreTest('ignore', paths=['/ignore'])
        )
        url = 'http://example.com/ignore'
        self.spider.add_urls([url])

        self.assertSetEqual(
            self.spider.urls_to_visit,
            {
                URL('https://example.com')
            }
        )

    def test_url_ignore_regex_test(self):
        self.spider._meta.url_ignore_tests.append(
            URLIgnoreRegexTest('ignore', r'\/ignore')
        )
        url = 'http://example.com/ignore'
        self.spider.start()
        self.spider.add_urls([url])

        self.assertSetEqual(
            self.spider.urls_to_visit,
            {
                URL('https://example.com')
            }
        )


class CustomSpider(SiteCrawler):
    class Meta:
        crawl = True
        start_urls = [
            'https://www.etam.com/'
        ]


class TestSpiderWithFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings['WEBDRIVER'] = 'Edge'
        settings['MEDIA_FOLDER'] = pathlib.Path(
            './tests/testproject/media'
        ).absolute()
        cls.settings = settings

    def test_execution(self):
        instance = CustomSpider()
        instance.start()


class TestSpiderWithRedis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings['STORAGES'] = {
            'default': 'kryptone.data_storages.RedisStorage',
            'backends': []
        }
        settings['STORAGE_REDIS_USERNAME'] = None
        settings['STORAGE_REDIS_PASSWORD'] = 'django-local-testing'
        settings['WEBDRIVER'] = 'Edge'
        settings['MEDIA_FOLDER'] = pathlib.Path(
            './tests/testproject/media'
        ).absolute()
        cls.settings = settings

    def test_execution(self):
        instance = CustomSpider()
        instance.start()
