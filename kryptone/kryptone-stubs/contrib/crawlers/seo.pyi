from typing import override
from kryptone.mixins import SEOMixin
from kryptone.utils.urls import URL


class SEOCrawlerMixin(SEOMixin):
    @override
    def resume(
        self,
        **kwargs
    ) -> None: ...

    @override
    def current_page_actions(
        self,
        current_url: URL,
        **kwargs
    ) -> None: ...
