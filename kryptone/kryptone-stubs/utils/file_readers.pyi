from typing import List, Callable, Union


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
