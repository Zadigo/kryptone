from typing import Generator, List, Callable, Literal, Union
from functools import cached_property


def tokenize(func: Callable) -> Callable[[str, bool], List[str]]: ...


def get_media_folder(filename: str) -> str: ...


@tokenize
def read_document(filename: str) -> str: ...


def read_documents(*filenames) -> List[str]: ...


def read_json_document(filename) -> List[dict]: ...


def write_json_document(
    filename: str, 
    data: Union[list[dict], dict]
) -> None: ...


def read_csv_document(filename: str, flatten: bool = ...) -> List[str]: ...


def write_csv_document(
    filename: str,
    data: list[str, int],
    adapt_data: bool = ...
) -> None: ...


def write_text_document(
    filename: str, 
    data: str,
    encoding: str = ...
) -> None: ...


class LoadStartUrls:
    filename: str = Literal['start_urls.json']

    def __init__(self, filename: str = None) -> None: ...
    def __iter__(self) -> Generator[str]: ...

    @cached_property
    def content(self) -> set[str]: ...
