from kryptone.mixins import EmailMixin
from kryptone.utils.urls import URL
from typing import override

class SearchLeadsMixin(EmailMixin):
    @override
    def current_page_actions(
        self, 
        current_url: URL, 
        **kwargs
    ) -> None: ...
