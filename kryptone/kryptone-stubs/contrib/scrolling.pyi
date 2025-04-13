from typing import Literal


class ScrollMixin:
    def scroll_window(
        self,
        wait_time: int = Literal[5],
        increment: int = Literal[1000],
        stop_at: int = None
    ) -> None: ...

    def scroll_page_section(
        self,
        xpath: str = None,
        css_selector: str = None
    ) -> str: ...

    def scroll_into_view(
        self,
        css_selector: str
    ) -> None: ...
