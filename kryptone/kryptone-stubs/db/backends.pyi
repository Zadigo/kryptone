import pathlib
import sqlite3
from functools import cached_property
from sqlite3 import Row
from typing import (Any, Callable, DefaultDict, Generator, List, Literal,
                    OrderedDict, Tuple, Type, Union)


class Functions:
    backend: SQLiteBackend = ...

    def __init__(self) -> None: ...

    def functions_sql(self) -> str: ...


class Lower(Functions):
    field_name: str = ...

    def __init__(self, field_name: str) -> None: ...
    def __str__(self) -> str: ...

    def function_sql(self) -> str: ...


class Upper(Lower):
    ...


class SQL:
    ALTER_TABLE = 'alter table {table} add column {params}'
    CREATE_TABLE = 'create table if not exists {table} ({fields})'
    DROP_TABLE = 'drop table if exists {table}'
    DELETE = 'delete from {table}'
    INSERT = 'insert into {table} ({fields}) values({values})'
    SELECT = 'select {fields} from {table}'
    UPDATE = 'update {table} set {params}'

    AND = 'and {rhv}'
    OR = 'or {rhv}'

    EQUALITY = '{field}={value}'
    LIKE = '{field} like {conditions}'
    BETWEEN = 'between {lhv} and {rhv}'
    IN = '{field} in ({values})'
    NOT_LIKE = '{field} not like {wildcard}'
    WHERE_CLAUSE = 'where {params}'
    WHERE_NOT = 'where not ({params})'

    WILDCARD_MULTIPLE = '%'
    WILDCARD_SINGLE = '_'

    ASCENDING = '{field} asc'
    DESCENDNIG = '{field} desc'

    ORDER_BY = 'order by {conditions}'

    @staticmethod
    def quote_value(value: Any) -> str: ...
    @staticmethod
    def comma_join(values: List[str]) -> str: ...

    @staticmethod
    def simple_join(
        values: List[str],
        space_characters: bool = ...
    ) -> str: ...

    @staticmethod
    def finalize_sql(sql: str) -> str: ...
    @staticmethod
    def de_sqlize_statement(sql: str) -> str: ...

    def quote_startswith(self, value: str) -> str: ...
    def quote_endswith(self, value: str) -> str: ...
    def quote_like(self, value: str) -> str: ...

    def dict_to_sql(
        self,
        data: dict[str, int, float],
        quote_values: bool = ...
    ) -> Tuple[list[str], list[str]]: ...

    def build_script(self, *sqls) -> str: ...
    def decompose_filters(self, **kwargs) -> List[Tuple[str]]: ...
    def build_filters(self, items: List[Tuple[str]]) -> List[str]: ...
    def build_annotation(self, **conditions) -> List[str]: ...


class SQLiteBackend(SQL):
    database: str = ...
    connection: sqlite3.Connection = ...

    def list_table_columns_sql(self, table) -> list[BaseRow]: ...
    def create_table_fields(self, table, columns_to_create) -> list: ...
    def list_tables_sql(self) -> list[BaseRow]: ...


class BaseRow(Row):
    backend_class: SQLiteBackend = ...

    def __repr__(self) -> str: ...
    def __contains__(self, value: str) -> bool: ...
    def __eq__(self, value: str) -> bool: ...
    @property
    def initialize_backend(self) -> SQLiteBackend: ...
    # def delete() -> None: ...


class Migrations:
    CACHE: dict = ...
    backend_class = Type[SQLiteBackend]
    file: pathlib.Path = ...
    file_id: str = ...
    tables: dict = ...
    migration_table_map: list[str] = ...
    fields_map: DefaultDict[list] = ...
    tables_for_creation: set = ...
    tables_for_deletion: set = ...
    existing_tables: set = ...
    has_migrations: bool = ...

    def __init__(self) -> None: ...
    def __repr__(self) -> str: ...

    @cached_property
    def read_content(self) -> dict: ...

    def _write_fields(self, table: Table) -> None: ...
    def _write_indexes(self, table: Table) -> list: ...
    def create_migration_table(self) -> None: ...
    def check(self, table_instances: dict[str, Table] = ...) -> None: ...
    def check_fields(self, table: Table, backend: SQLiteBackend) -> None: ...
    def migrate(self, tables: List[Table]) -> None: ...
    def get_table_fields(self, name: str) -> list[dict[str]]: ...
    def reconstruct_table_fields(self, table: Table) -> list[Field]: ...


class Field:
    python_type: str = ...
    base_validators: list = ...
    name: str = ...
    null: bool = ...
    primary_key: bool = ...
    default: Any = ...
    unique: bool = ...
    table: Table = ...
    base_field_parameters: list[Union[Literal['text'],
                                      Literal['integer'], Literal['blob']], Literal['not null']] = ...

    def __init__(
        self,
        name: str,
        *,
        null: bool = ...,
        primary_key: bool = ...,
        default: Any = ...,
        unique: bool = ...,
        validators: list[Callable[[str], None]] = ...
    ) -> None: ...

    def __repr__(self) -> str: ...

    def __hash__(self) -> int: ...
    def __eq__(self, value: str) -> bool: ...
    # @property
    # def field_type(self) -> Union[str]: ...

    @classmethod
    def create(
        cls,
        name: str,
        params: list[str],
        verbose_name: str = ...
    ) -> Field: ...

    def to_python(self, data: Any) -> Any: ...
    def to_database(self, data: Any) -> str: ...
    def field_parameters(self) -> list[str]: ...
    def prepare(self, table: Table) -> None: ...
    def deconstruct(self) -> Tuple[str, None, list[str]]: ...


class CharField(Field):
    ...


class IntegerField(Field):
    ...


class JSONField(Field):
    ...


class BooleanField(Field):
    truth_types: list[str] = ...
    false_types: list[str] = ...


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

    def __init__(self, query: Query): ...
    def __str__(self) -> str: ...
    def __iter__(self) -> Generator[BaseRow]: ...

    def load_cache(self) -> None: ...
    def exclude(self, **kwargs) -> QuerySet[BaseRow]: ...
    def order_by(self, *fields) -> QuerySet[BaseRow]: ...


class BaseTable(type):
    def __new__(cls, name: str, bases: tuple, attrs: dict) -> type: ...
    @classmethod
    def prepare(cls, table: type) -> None: ...


class AbstractTable(metaclass=BaseTable):
    query_class: Type[Query] = ...
    backend_class: Type[SQLiteBackend] = ...
    backend: SQLiteBackend = ...

    def __init__(self, database: str = ...) -> None: ...
    def __hash__(self) -> int: ...

    def validate_values(self, fields, values) -> Any: ...
    def all(self) -> list[BaseRow]: ...
    def filter(self, **kwargs) -> list[BaseRow]: ...
    def first(self) -> BaseRow: ...
    def last(self) -> BaseRow: ...
    def create(self, **kwargs) -> BaseRow: ...
    def get(self, **kwargs) -> Union[BaseRow, None]: ...


class Table(AbstractTable):
    fields_map: OrderedDict = ...
    name: str = ...
    query: Query = ...

    def __init__(
        self,
        name: str,
        database: str,
        *,
        fields: list[str] = ...
    ) -> None: ...

    def __repr__(self) -> str: ...

    def has_field(self, name: str) -> bool: ...
    def create_table_sql(self, fields: list[str]) -> list[str]: ...
    def drop_table_sql(self, name: str) -> list[str]: ...
    def build_field_parameters(self) -> list[str]: ...
    def prepare(self) -> None: ...


class Database:
    migrations: Migrations = ...
    migrations_class: Type[Migrations] = ...
    table_map: dict[str, Table] = {}
    database_name: str = ...
    table_instances: list[Table] = ...

    def __init__(self, name: str, *tables: Table): ...
    def __repr__(self) -> str: ...
    def __getitem__(self, table_name: str) -> Table: ...

    def get_table(self, table_name: str) -> Table: ...
    def make_migrations(self) -> None: ...
    def migrate(self) -> None: ...
