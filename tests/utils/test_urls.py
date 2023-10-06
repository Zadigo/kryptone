import unittest

from kryptone.utils.urls import URL, CompareUrls, URLPassesTest, UrlPassesRegexTest


class TestUrl(unittest.TestCase):
    def setUp(self):
        url = 'https://www.defacto.com/fr-ma/coool-fitted-kisa-kollu-tisort-2836888'
        self.instance = URL(url)

    def test_structural(self):
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

    def test_capturing(self):
        result = self.instance.capture(r'[a-z]+\-(\d+)')
        self.assertTrue(result.group(1) == '2836888')

    def test_test_path(self):
        result = self.instance.test_path(r'[a-z]+\-(\d+)')
        self.assertTrue(result)

    def test_is_path(self):
        self.assertFalse(self.instance.is_path)

    def test_is_valid(self):
        self.assertTrue(self.instance.is_valid)

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

    def test_pagination(self):
        url = 'http://example/[1]'


# class TestUrlTesting(unittest.TestCase):
#     def test_result(self):
#         self.assertTrue(TestUrl('http://example.com', 'http://example.com/'))
#         self.assertFalse(
#             TestUrl('http://example.com/1', 'http://example.com/'))

#         url1 = 'https://www.defacto.com/fr-ma'
#         url2 = 'https://www.defacto.com/fr-ma/fall-in-love-oversize-fit-kisa-kollu-takim-2808204'
#         self.assertFalse(TestUrl(url1, url2))


IGNORE_URLS = [
    '/Customer/Wishlist',
    '/fr-ma/corporate/contact-us',
    'new-member'
]

URLS = [
    'https://www.defacto.com/fr-ma/statik/new-member',
    'https://www.defacto.com/fr-ma/Customer/Wishlist'
]


class TestUrlPassesTest(unittest.TestCase):
    def test_result(self):
        instance = URLPassesTest('base_pages', paths=IGNORE_URLS)

        for url in URLS:
            with self.subTest(url=url):
                self.assertFalse(instance(url))

    def test_multiple_results(self):
        instances = [
            URLPassesTest('base_pages', paths=IGNORE_URLS),
            UrlPassesRegexTest('other_pages', regex=r'\/static\/')
        ]
        for url in URLS:
            with self.subTest(url=url):
                pass


if __name__ == '__main__':
    unittest.main()
