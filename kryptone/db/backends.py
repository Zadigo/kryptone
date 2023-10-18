from collections import OrderedDict, defaultdict
import datetime
from functools import cached_property
import json
import sqlite3
import secrets

# {
#     "id": "fe81zef5",
#     "date": null,
#     "number": 1,
#     "tables": [
#         {
#             "name": "urls_seen",
#             "fields": [
#                 {
#                     "name": "my_name",
#                     "verbose_name": null,
#                     "params": "text null"
#                 }
#             ],
#             "indexes": [
#                 "my_name"
#             ]
#         }
#     ]
# }

class Migrations:
    CACHE = {}

    def __init__(self):
        self.CACHE = self.read_content
        try:
            self.tables = self.CACHE['tables']
        except KeyError:
            raise KeyError('Migration file is not valid')
        self.table_map = [table['name'] for table in self.tables]
        self.fields_map = defaultdict(list)

    def __repr__(self):
        return f'<{self.__class__.__name__} [something]>'
        
    @cached_property
    def read_content(self):
        with open('Z:/- RESPONSABLE DIGITAL/SCRIPTS/kryptone/kryptone/db/migrations.json', mode='r') as f:
            return json.load(f)
        
    def _create_fields(self, table):
        fields_map = []
        for field in table.get_fields():
            fields_map.append(field.deconstruct())
        self.fields_map[table] = fields_map
    
    def _create_indexes(self, table):
        return []
        
    def migrate(self, table):
        with open('Z:/- RESPONSABLE DIGITAL/SCRIPTS/kryptone/kryptone/db/migrations.json', mode='r'):
            self.CACHE['id'] = secrets.token_hex(5)
            self.CACHE['date'] = datetime.datetime.now()
            self.CACHE['number'] = self.CACHE['number'] + 1
            self.CACHE['tables'].append({
                'name': table.name,
                'fields': self._create_fields(table),
                'indexes': self._create_indexes(table)
            })

    def get_table_fields(self, name):
        table_index = self.table_map.index(name)
        return self.tables[table_index]['fields']
    
    def construct_fields(self, name):
        fields = self.get_table_fields(name)

        items = []
        for field in fields:
            params = []
            for value in field.values():
                params.append(value)
            items.append(params)
        return items

# migrations = Migrations()
# print(migrations.construct_fields('urls_seen'))


class Field:
    def __init__(self, name, *, null=False, primary_key=False, default=None):
        self.name = name
        self.null = null
        self.primary_key = primary_key
        self.default = default
        self.table = None

    def __repr__(self):
        return f'<{self.__class__.__name__}[{self.name}]>'

    def __hash__(self):
        return hash((self.name))

    def field_parameters(self):
        base_parameters = ['text', 'not null']
        if self.null:
            base_parameters.pop(base_parameters.index('not null'))
            base_parameters.append('null')

        if self.primary_key:
            base_parameters.append('primary key')

        if self.default is not None:
            value = self.table.quote_value(self.default)
            base_parameters.extend(['default', value])
        base_parameters.insert(0, self.name)
        return base_parameters

    def prepare(self, table):
        if not isinstance(table, Table):
            raise ValueError()
        self.table = table

    def deconstruct(self):
        field_parameters = ' '.join(self.field_parameters())
        return (self.name, None, field_parameters)


class TableRegistry:
    table_map = OrderedDict()
    table_names = []
    active_tables = set()

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.number_of_tables}]>'

    @property
    def number_of_tables(self):
        return len(self.table_map.keys())

    def add_table(self, name, table):
        self.table_map[name] = table
        self.table_names.append(name)

    def table_exists(self, name):
        return name in self.table_names
    
    def set_active_tables(self, tables):
        self.active_tables.update(tables)

    def inactive_tables(self):
        return set(self.active_tables).difference(self.table_names)


registry = TableRegistry()


class SQL:
    CREATE_TABLE = 'create table if not exists {table} ({fields})'
    DROP_TABLE = 'drop table if exists {table}'
    INSERT = 'insert into {table} ({fields}) values({values})'
    SELECT = 'select {fields} from {table}'

    AND = 'and {rhv}'
    OR = 'or {rhv}'

    EQUALITY = '{field}={value}'
    NOT_LIKE = '{field} not like {wildcard}'
    WHERE_CLAUSE = 'where {params}'

    @staticmethod
    def quote_value(value):
        if isinstance(value, int):
            return value

        if value.startswith("'"):
            return value
        return f"'{value}'"

    @staticmethod
    def comma_join(values):
        return ', '.join(values)

    @staticmethod
    def simple_join(values):
        return ' '.join(values)

    @staticmethod
    def finalize_sql(sql):
        if sql.endswith(';'):
            return sql
        return f'{sql};'

    def dict_to_sql(self, data):
        fields = list(data.keys())
        quoted_value = list(map(lambda x: self.quote_value(x), data.values()))
        return fields, quoted_value

    def build_script(self, *sqls):
        return '\n'.join(map(lambda x: self.finalize_sql(x), sqls))


class SQLiteBackend(SQL):
    def __init__(self, database=None):
        if database is None:
            database = ':memory:'
        else:
            database = f'{database}.sqlite'
        self.database = database
        connection = sqlite3.connect(database)
        self.connection = connection


class Query:
    def __init__(self, table, sql_tokens):
        self._sql = None
        self._sql_tokens = sql_tokens
        self._table = table
        self.result_cache = []

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self._sql}]>'

    def prepare_sql(self):
        sql = self._table.backend.simple_join(self._sql_tokens)
        self._sql = self._table.backend.finalize_sql(sql)

    def run(self, commit=False):
        self.prepare_sql()
        result = self._table.backend.connection.execute(self._sql)
        if commit:
            self._table.backend.connection.commit()
        self.result_cache = list(result)


class QuerySet:
    def __init__(self, query):
        self.query = query
        self.result_cache = []

    def __str__(self):
        self.load_cache()
        return self.result_cache

    def __iter__(self):
        self.load_cache()
        for item in self.result_cache:
            yield item

    def load_cache(self):
        if self.result_cache is None:
            self.result_cache = self.query.run()


class BaseTable(type):
    def __new__(cls, name, bases, attrs):
        super_new = super().__new__
        if 'prepare' in attrs:
            new_class = super_new(cls, name, bases, attrs)
            cls.prepare(new_class)
            return new_class
        return super_new(cls, name, bases, attrs)

    @classmethod
    def prepare(cls, table):
        pass


class AbstractTable(metaclass=BaseTable):
    query_class = Query
    backend_class = SQLiteBackend

    def __init__(self, database=None):
        self.backend = self.backend_class(database=database)
        registry.add_table(self.name, self)

    def create(self, **kwargs):
        fields, values = self.backend.dict_to_sql(kwargs)
        joined_fields = self.backend.comma_join(fields)
        joined_values = self.backend.comma_join(values)
        sql = self.backend.INSERT.format(
            table=self.name,
            fields=joined_fields,
            values=joined_values
        )
        query = self.query_class(self, [sql])
        query.run(commit=True)


class Table(AbstractTable):
    fields_map = OrderedDict()

    def __init__(self, name, database, *, fields=[]):
        self.name = name
        self.query = None
        super().__init__(database=database)

        for field in fields:
            if not isinstance(field, Field):
                raise ValueError()

            # if field.name in self.fields_map:
            #     raise ValueError()

            field.prepare(self)
            self.fields_map[field.name] = field
        self.prepare()

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.name}]>'

    def create_table_sql(self, fields):
        sql = self.backend.CREATE_TABLE.format(
            table=self.name,
            fields=fields
        )
        return [sql]

    def drop_table_sql(self, name):
        sql = self.backend.DROP_TABLE.format(
            table=name
        )
        return [sql]

    def list_tables_sql(self):
        sql = self.backend.SELECT.format(
            fields='name',
            table='sqlite_schema'
        )
        not_like_clause = self.backend.NOT_LIKE.format(
            field='name',
            wildcard=self.backend.quote_value('sqlite_%')
        )
        where_clause = self.backend.WHERE_CLAUSE.format(
            params=self.backend.simple_join([
                self.backend.EQUALITY.format(
                    field='type',
                    value=self.backend.quote_value('table')
                ),
                self.backend.AND.format(rhv=not_like_clause)
            ])
        )
        query = self.query_class(self, [sql, where_clause])
        self.query = query
        query.run()
        return query.result_cache

    def build_field_parameters(self):
        return [
            field.field_parameters()
            for field in self.fields_map.values()
        ]

    def prepare(self):
        field_params = self.build_field_parameters()
        field_params = [self.backend.simple_join(params) for params in field_params]
        sql = self.create_table_sql(self.backend.comma_join(field_params))
        query = self.query_class(self, sql)
        self.query = query
        query.run(commit=True)

        # active_sql_tables = [item[0] for item in self.list_tables_sql()]
        # registry.set_active_tables(active_sql_tables)
        
        # inactive_tables = registry.inactive_tables()
        # if inactive_tables:
        #     script_tokens = []
        #     for name in inactive_tables:
        #         script_tokens.extend(self.drop_table_sql(name))
        #     sql = self.backend.build_script(*script_tokens)
        #     query = self.query_class(self, script_tokens)
        #     query.run(commit=True)


# table = Table('seen_urls', 'scraping', fields=[
#     Field('url')
# ])
# table.create(url='http://example.com')
# table.create(url='http://example/1')
