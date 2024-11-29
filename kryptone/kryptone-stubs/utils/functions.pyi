import pathlib
from typing import Union

from kryptone.utils.urls import URL


def directory_from_breadcrumbs(
    text: str,
    separator: str = ...,
    remove_last: bool = ...,
    exclude: list[str] = ...
) -> pathlib.Path: ...


def directory_from_url(
    url_or_path: Union[URL, str],
    exclude: list[str] = ...
) -> pathlib.Path: ...


def create_filename(
    length: int = ...,
    extension: str = ...,
    suffix: str = ...,
    suffix_with_date: bool = ...
) -> str: ...
