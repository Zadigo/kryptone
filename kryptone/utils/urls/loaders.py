import csv
import itertools
import json


from kryptone.conf import settings
from kryptone.exceptions import NoStartUrlsFile
from kryptone.utils.urls.generators import BaseURLGenerator


class LoadStartUrls(BaseURLGenerator):
    """The class loads start URLs from a CSV or JSON file
    to be used by a web crawler. This allows for automated operations on
    the pages specified by these URLs

    The class takes a filename (without the extension) and a flag indicating
    whether the file is in JSON format. It then loads the URLs from the
    specified file and makes them available for the crawler.

    >>> class MyCrawler(SiteCrawler):
    ...     class Meta:
    ...         start_urls = LoadStartUrls()

    The class can also laod urls from the internet by running a request
    to an api endpoint
    """

    def __init__(self, *, filename=None, is_json=False):
        self.is_json = is_json
        extension = "json" if self.is_json else "csv"
        self.filename = f"{filename or 'start_urls'}.{extension}"

    def resolve_generator(self):
        try:
            path = settings.PROJECT_PATH / self.filename
            with open(path, mode="r", encoding="utf-8") as f:
                if self.is_json:
                    data = json.load(f)
                    for item in data:
                        if isinstance(item, dict):
                            yield item["url"]

                        if isinstance(item, str):
                            yield item
                else:
                    yield from list(itertools.chain(*csv.reader(f)))
        except FileNotFoundError:
            raise NoStartUrlsFile()
