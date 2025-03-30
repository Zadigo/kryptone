import unittest

from kryptone.utils.urls import URL

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

    def test_test_path(self):
        result = self.instance.test_path(r'[a-z]+\-(\d+)')
        self.assertTrue(result)

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
        self.assertIn('http://example.com', urls)
        # TODO: When trying to check the presence of
        # string in the set, it uses the __hash__
        # which are not the same

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
