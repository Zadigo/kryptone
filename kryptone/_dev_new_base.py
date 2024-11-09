import dataclasses

from kryptone._new_base import SiteCrawler
from kryptone.conf import settings

setattr(settings, 'WAIT_TIME', 25)


@dataclasses.dataclass
class CustomData:
    title: str


class CustomSpider(SiteCrawler):
    model = CustomData

    class Meta:
        debug_mode = False
        start_urls = ['https://www.hunkemoller.fr']


try:
    c = CustomSpider(browser_name='Edge')
    # c.start()
    c.resume()
except KeyboardInterrupt:
    pass
