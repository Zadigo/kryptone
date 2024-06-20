from typing import Generator, List

from kryptone.db.backends import BaseRow, SQLiteBackend
from kryptone.db.tables import Table


class Query:
    _table: Table = ...
    _backend: SQLiteBackend = ...
    _sql: str = ...
    _sql_tokens: list[str] = ...
    result_cache: list[BaseRow] = ...

    def __init__(
        self,
        backend: SQLiteBackend,
        sql_tokens: list[str],
        table: Table = ...
    ): ...

    def __repr__(self) -> str: ...
    def __del__(self) -> None: ...

    @classmethod
    def run_multiple(
        cls,
        backend: SQLiteBackend,
        *sqls,
        **kwargs
    ) -> Generator[Query]: ...

    @classmethod
    def create(
        cls,
        backend: SQLiteBackend,
        sql_tokens: List[str],
        table: Table = ...
    ) -> Query: ...

    def prepare_sql(self) -> None: ...
    def run(self, commit: bool = ...) -> None: ...


class QuerySet:
    query: Query = ...
    result_cache: list[BaseRow] = ...

    def __init__(self, query: Query) -> None: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...
    def __getitem__(self, index: int) -> BaseRow: ...
    def __iter__(self) -> Generator[BaseRow]: ...

    def load_cache(self) -> None: ...
    def exclude(self, **kwargs: str) -> QuerySet[BaseRow]: ...
    def order_by(self, *fields: str) -> QuerySet[BaseRow]: ...
    def values(self, *fields: str) -> list[dict]: ...