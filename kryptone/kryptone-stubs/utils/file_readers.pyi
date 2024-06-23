import pathlib
from functools import cached_property
from typing import Any, Callable, Generator, List, Literal, Union

def tokenize(func: Callable) -> Callable[[str], List[str]]: ...


def get_media_folder(filename: str) -> str: ...


@tokenize
def read_document(filename: str) -> str: ...


def read_documents(*filenames: str) -> List[str]: ...


def read_json_document(filename) -> List[dict]: ...


def write_json_document(
    filename: str,
    data: Union[list[dict], dict]
) -> None: ...


def read_csv_document(
    filename: str, flatten: bool = ...) -> List[List[Any]]: ...


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


# class LoadJS:
#     _project_path: pathlib.Path = ...
#     filename: str = ...
#     files: list = ...

#     def __init__(self, filename: str) -> None: ...
#     def __repr__(self) -> str: ...

#     @cached_property
#     def content(self) -> str: ...
