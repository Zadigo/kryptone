import unittest
from urllib.parse import urlparse, urlunparse
import pathlib
from kryptone.utils.file_readers import read_csv_document, read_document
from kryptone.conf import settings


IGNORE_QUERIES = True

IGNORE_IMAGES = True

URLS = read_csv_document(
    'E:/personnal/kryptone/tests/data/urls.csv', flatten=True)

DEFAULT_IMAGES_EXTENSIONS = read_document(
    settings.GLOBAL_KRYPTONE_PATH / 'data/image_extensions.txt', as_list=True
)


class URLSearchAlgorithm:
    urls_to_visit = set()
    list_of_seen_urls = set()
    visited_urls = set()
    _start_url_object = urlparse('https://www.lefties.com')

    def __init__(self, urls):
        print('Input urls', len(urls))
        for link in urls:
            # Turn the url into a Python object
            # to make it more usable for us
            link_object = urlparse(link)

            # We do not want to add an item
            # to the list if it already exists,
            # if it is invalid or None
            if link in self.urls_to_visit:
                continue

            if link in self.visited_urls:
                continue

            logic = [
                link is None,
                link == '',
                link_object.netloc == '' and link_object.path == ''
            ]
            if any(logic):
                continue

            # Links such as http://exampe.com#
            # are useless and can create
            # useless repetition for us
            if link.endswith('#'):
                continue

            # If the link is similar to the initially
            # visited url, skip it.
            # NOTE: This is essentially a  security measure
            if link_object.netloc != self._start_url_object.netloc:
                continue

            # If the url contains a fragment, it is the same
            # as visiting the root page, for example:
            # example.com/#google is the same as example.com/
            if link_object.fragment:
                continue

            # If we have already visited the home page then
            # skip all urls that include the '/' path.
            # NOTE: This is another security measure
            if link_object.path == '/' and self._start_url_object.path == '/':
                continue

            # Reconstruct a partial url for example
            # /google becomes https://example.com/google
            if link_object.path != '/' and link.startswith('/'):
                # link = f'{self._start_url_object.scheme}://{self._start_url_object.netloc}{link}'
                link = urlunparse((
                    self._start_url_object.scheme,
                    self._start_url_object.netloc,
                    link,
                    None,
                    None,
                    None
                ))

            if IGNORE_QUERIES:
                if link_object.query != '':
                    continue

            if IGNORE_IMAGES:
                path = pathlib.Path(link)
                if path != '':
                    if path.suffix in DEFAULT_IMAGES_EXTENSIONS:
                        continue

            self.urls_to_visit.add(link)
            # For statistics, we'll keep track of all the
            # urls that we have gathered during crawl
            self.list_of_seen_urls.add(link)

    def __iter__(self):
        for url in self.urls_to_visit:
            yield url

# class TestSearchUrls(unittest.TestCase):
#     def test_urls(self):
#         instance = URLSearchAlgorithm(URLS)


# if __name__ == '__main__':
#     unittest.main()

instance = URLSearchAlgorithm(URLS)
print(len(sorted(list(instance))))
