import json
import pathlib
import unittest
from urllib.parse import urlunparse

from kryptone.utils.urls import URL, URLIgnoreRegexTest, URLIgnoreTest

IGNORE_PATHS = [
    '/Customer/Wishlist',
    '/fr-ma/corporate/contact-us',
    'new-member',
    '/baby'
]


URLS = [
    'https://www.defacto.com/fr-ma/statik/new-member',
    'https://www.defacto.com/fr-ma/Customer/Wishlist',
    'https://www.defacto.com/fr-ma/baby',
    'https://www.defacto.com/fr-ma/woman'
]


class TestUrl(unittest.TestCase):
    def setUp(self):
        url = 'https://www.defacto.com/fr-ma/coool-fitted-kisa-kollu-tisort-2836888'
        self.instance = URL(url)

    def test_structure(self):
        self.assertTrue('kollu-' in self.instance)
        self.assertFalse(self.instance.is_path)
        self.assertTrue(self.instance.is_valid)
        self.assertFalse(self.instance.has_fragment)
        self.assertFalse(self.instance.is_file)
        self.assertTrue(
            self.instance.url_stem == 'coool-fitted-kisa-kollu-tisort-2836888'
        )
        self.assertTrue(self.instance.is_same_domain(
            'https://www.defacto.com/fr-ma'
        ))
        self.assertFalse(self.instance.compare('http://example.com'))

        new_instance = self.instance.create('http://example.com#fast')
        self.assertTrue(new_instance.has_fragment)

        new_instance = self.instance.create('http://example.com/fast.pdf')
        self.assertTrue(new_instance.is_file)

        new_instance = self.instance.create('http://example.com?q=true')
        self.assertIsInstance(new_instance.query, dict)

    def test_capturing(self):
        result = self.instance.capture(r'[a-z]+\-(\d+)')
        self.assertTrue(result.group(1) == '2836888')

    def test_testing_path_regex(self):
        result = self.instance.test_path(r'[a-z]+\-(\d+)')
        self.assertTrue(result)

        # Check that / and and /1 for example are matched
        # differently by the function
        url = URL('http://example.com/1')
        result = url.test_path(r'\d+')
        self.assertTrue(result, 'Path should be matched as a digit')

        result = url.test_path(r'\/')
        self.assertTrue(result, 'Path should not be matched as /')

    def test_test_multiple_paths(self):
        regexes = [r'\d+']

        url = URL('http://example.com/1')
        result = url.multi_test_path(regexes, operator='and')
        self.assertTrue(result, 'Path should be a digit')

        url = URL('http://example.com')
        result = url.multi_test_path(regexes, operator='and')
        self.assertFalse(result, 'Path should not be a digit')

        regexes = [r'\d+', r'fast\-\d+']

        url = URL('http://example.com/1')
        result = url.multi_test_path(regexes, operator='and')
        self.assertFalse(result, 'Path should be a digit and fast-1')

        regexes = [r'\/$', r'\d+']
        url = URL('http://example.com/1')
        result = url.multi_test_path(regexes, operator='or')
        self.assertTrue(result, 'Path should be either / or a digit')

    def test_is_path(self):
        self.assertFalse(self.instance.is_path)

    def test_is_valid(self):
        self.assertTrue(self.instance.is_valid)

    def test_is_image(self):
        url = 'https://static.bershka.net/4/photos2/2024/V/0/1/p/8936/256/800//01/ab1c523937698d85bb1dfe3953bbd6f7-8936256800_2_3_0.jpg'
        self.assertTrue(URL(url).is_image)

    def test_has_fragment(self):
        self.assertFalse(self.instance.has_fragment)
        url = 'https://www.lefties.com/ma/woman/clothing/knit-c1030267524.html#'
        url = self.instance.create(url)
        self.assertTrue(url.has_fragment)

    def test_is_file(self):
        self.assertFalse(self.instance.is_file)
        url = 'https://www.lefties.com/ma/woman/clothing/knit-c1030267524.html'
        url = self.instance.create(url)
        self.assertTrue(url.is_file)

    def test_test_url(self):
        url = 'https://www.lefties.com/ma/woman/clothing/knit-c1030267524.html'
        url = self.instance.create(url)
        self.assertTrue(url.test_url(r'\/clothing\/'))

    def test_test_path(self):
        url = 'https://www.lefties.com/ma/woman/clothing/knit-c1030267524.html'
        url = self.instance.create(url)
        self.assertTrue(url.test_path(r'\/clothing\/'))

    def test_decompose_path(self):
        expected = ['fr-ma', 'coool-fitted-kisa-kollu-tisort-2836888']
        self.assertListEqual(expected, self.instance.decompose_path())
        self.assertIn('fr-ma', self.instance.decompose_path())

    def test_path_decomposition(self):
        tokens = self.instance.decompose_path()
        self.assertListEqual(
            tokens, ['fr-ma', 'coool-fitted-kisa-kollu-tisort-2836888']
        )

    def test_contains(self):
        urls = [
            URL('http://example.com'),
            URL('http://example.com/1')
        ]
        self.assertIn(URL('http://example.com'), urls)

        # Cannot compare strings
        with self.assertRaises(AssertionError):
            self.assertIn('http://example.com', urls)

    def test_inversion(self):
        url = URL('http://example.com')
        self.assertFalse(~url)

    # def test_and(self):
    #     url = URL('http://example.com')
    #     url2 = URL('http://example.com/2')
    #     print(url & url2)

    def test_is_same_domain(self):
        domain = 'https://www.defacto.com'
        self.assertTrue(self.instance.is_same_domain(domain))

    def test_compare(self):
        a = URL('http://example.com')
        b = URL('http://example.com?q=true')
        self.assertTrue(a.compare(b))

        b = 'http://example.com?q=true'
        self.assertTrue(a.compare(b))

    def test_remove_fragment(self):
        result = URL('http://example.com#home')
        new_url = result.remove_fragment()
        self.assertFalse(new_url.has_fragment)

    def test_properties(self):
        url = 'https://static.bershka.net/assets/public/1174/9ac3/e8384037903b/afaee790a05e/00623152505-a3f/00623152505-a3f.jpg?ts=1717510394290&w=800'

        instance = URL(url)
        self.assertTrue(instance.has_query)
        self.assertTrue(instance.has_path)

        self.assertEqual('00623152505-a3f.jpg', instance.get_filename)

    def test_rebuild_query(self):
        instance = URL('http://example.com')
        result = instance.rebuild_query(a=1)
        self.assertEqual(str(result), 'http://example.com?a=1')

        instance = URL('http://example.com?b=2')
        result = instance.rebuild_query(c=4)
        self.assertEqual(str(result), 'http://example.com?c=4&b=2')

    def test_pass_anything(self):
        values = [
            'http://example.com',
            URL('http://example.com'),
            None,
            12345,
            lambda: 'http://example.com',
            '/some/path',
            urlunparse(('http', 'example.com', '/path', '', '', ''))
        ]

        for value in values:
            with self.subTest(value=value):
                instance = URL(value)
                print(instance.is_valid)

    def test_query(self):
        instance = URL('http://example.com?a=1&b=2&c=3')
        self.assertEqual(instance.query, {'a': ['1'], 'b': ['2'], 'c': ['3']})
        self.assertTrue(instance.has_query)


class TestURLIgnoreTest(unittest.TestCase):
    def setUp(self):
        path = pathlib.Path(__file__).parent.parent.absolute()
        with open(path / 'data' / 'urls.json', mode='r') as f:
            self.urls = json.load(f)

    def test_ignore_paths(self):
        instance = URLIgnoreTest('test-name', paths=['/femmes/vetements'])

        url_count = len(
            list(
                filter(
                    lambda u: '/femmes/vetements' in u,
                    self.urls
                )
            )
        )

        self.assertGreater(
            url_count, 0,
            'Test URLs must contain at least one matching URL'
        )

        total_tests = 0
        for url in self.urls:
            with self.subTest(url=url):
                result = instance(url)

                if '/femmes/vetements' in url:
                    # Was ignored
                    self.assertTrue(result)
                    total_tests += 1
                else:
                    self.assertFalse(result)

        self.assertEqual(
            total_tests,
            url_count,
            'All matching URLs should have been tested'
        )

    def test_ignore_paths_regex(self):
        instance = URLIgnoreRegexTest(
            'test-name',
            regex=r'\/minijupe\-denim'
        )

        url_count = len(
            list(
                filter(
                    lambda u: '/minijupe-denim' in u,
                    self.urls
                )
            )
        )

        self.assertGreater(
            url_count, 0,
            'Test URLs must contain at least one matching URL'
        )

        total_tests = 0
        for url in self.urls:
            with self.subTest(url=url):
                result = instance(url)

                if '/minijupe-denim' in url:
                    # Was ignored
                    self.assertTrue(result)
                    total_tests += 1
                else:
                    self.assertFalse(result)

        self.assertEqual(
            total_tests,
            url_count,
            'All matching URLs should have been tested'
        )
