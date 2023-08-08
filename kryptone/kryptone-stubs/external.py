from typing import TYPE_CHECKING

from kryptone.utils.urls import UrlPassesRegexTest, URLPassesTest

if TYPE_CHECKING:
    from typing import ClassVar, Union

    class TypedModelMeta:
        domains = ClassVar[list]
        audit_page = ClassVar[bool]
        debug_mode = ClassVar[bool]
        site_language = ClassVar[str]
        url_passes_tests = ClassVar[list[Union[UrlPassesRegexTest, URLPassesTest]]]
        default_scroll_step = ClassVar[int]
        gather_email = ClassVar[bool]
