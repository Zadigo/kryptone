from kryptone.base import SiteCrawler
from kryptone.mixins import EmailMixin
from kryptone.utils.urls import URL


class LeadsCrawler(SiteCrawler, EmailMixin):
    def current_page_actions(self, current_url: URL, **kwargs) -> None: ...
