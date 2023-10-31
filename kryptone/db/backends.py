import sqlite3

from kryptone.db import DATABASE
from kryptone.db.functions import Functions
from kryptone.db.queries import Query


class BaseRow:
    """Adds additional functionalities to
    the default SQLite `Row` class. Rows
    allows the data that comes from the database
    to be interfaced

    >>> row = table.get(name='Kendall')
    ... <BaseRow [{'rowid': 1}]>
    ... row['rowid']
    ... 1
    """

    _marked_for_update = False

    def __init__(self, cursor, fields, data):
        self._cursor = cursor
        self._fields = fields
        self._cached_data = data
        self._backend = None
        self._table = None

        for key, value in self._cached_data.items():
            setattr(self, key, value)

    def __repr__(self):
        return f'<id: {self.rowid}>'

    def __setitem__(self, key, value):
        self._marked_for_update = True
        setattr(self, key, value)
        result = self._backend.save_row(self, [key, value])
        self._marked_for_update = False
        return result

    def __getitem__(self, key):
        return getattr(self, key)
    
    def __hash__(self):
        return hash((self.rowid))

    def __contains__(self, value):
        truth_array = []
        for item in self._cached_data.values():
            if isinstance(item, int):
                item = str(item)
            truth_array.append(value in item)
        return any(truth_array)
        # return any((value in self[key] for key in self._fields))

    def __eq__(self, value):
        return any((self[key] == value for key in self._fields))

    def delete(self):
        pass


def row_factory(backend):
    """Base function to generate row that implement
    additional functionnalities on the results
    of the database"""
    def inner_factory(cursor, row):
        fields = [column[0] for column in cursor.description]
        data = {key: value for key, value in zip(fields, row)}
        instance = BaseRow(cursor, fields, data)
        instance._backend = backend
        return instance
    return inner_factory


class SQL:
    """Base sql compiler"""

    ALTER_TABLE = 'alter table {table} add column {params}'
    CREATE_TABLE = 'create table if not exists {table} ({fields})'
    CREATE_INDEX = 'create index {name} on {table} ({fields})'
    DROP_TABLE = 'drop table if exists {table}'
    DROP_INDEX = 'drop index if exists {value}'
    DELETE = 'delete from {table}'
    INSERT = 'insert into {table} ({fields}) values({values})'
    SELECT = 'select {fields} from {table}'
    UPDATE = 'update {table} set {params}'

    AND = 'and {rhv}'
    OR = 'or {rhv}'

    CONDITION = '{field}{operator}{value}'
    EQUALITY = '{field}={value}'
    LIKE = '{field} like {conditions}'
    BETWEEN = '{field} between {lhv} and {rhv}'
    IN = '{field} in ({values})'
    NOT_LIKE = '{field} not like {wildcard}'
    WHERE_CLAUSE = 'where {params}'
    WHERE_NOT = 'where not ({params})'

    WILDCARD_MULTIPLE = '%'
    WILDCARD_SINGLE = '_'

    ASCENDING = '{field} asc'
    DESCENDNIG = '{field} desc'

    ORDER_BY = 'order by {conditions}'
    # UNIQUE_INDEX = 'create unique index {name} ON {table}({fields})'

    LOWER = 'lower({field})'
    UPPER = 'upper({field})'
    LENGTH = 'length({field})'
    MAX = 'max({field})'
    MIN = 'min({field})'

    STRFTIME = 'strftime({format}, {value})'

    CHECK_CONSTRAINT = 'check ({conditions})'

    @staticmethod
    def quote_value(value):
        if isinstance(value, int):
            return value

        if value.startswith("'"):
            return value
        return f"'{value}'"

    @staticmethod
    def comma_join(values):
        def check_integers(value):
            if isinstance(value, (int, float)):
                return str(value)
            return value
        values = map(check_integers, values)
        return ', '.join(values)
    
    @staticmethod
    def operator_join(values, operator='and'):
        """Joins a set of values using a valid
        operator
        
        >>> self.condition_join(["name='Kendall'", "surname='Jenner'"])
        ... "name='Kendall' and surname='Jenner'"
        """
        return f' {operator} '.join(values)

    @staticmethod
    def simple_join(values, space_characters=True):
        def check_integers(value):
            if isinstance(value, (int, float)):
                return str(value)
            return value
        values = map(check_integers, values)

        if space_characters:
            return ' '.join(values)
        return ''.join(values)

    @staticmethod
    def finalize_sql(sql):
        if sql.endswith(';'):
            return sql
        return f'{sql};'

    @staticmethod
    def de_sqlize_statement(sql):
        if sql.endswith(';'):
            return sql.removesuffix(';')
        return sql

    @staticmethod
    def wrap_parenthentis(value):
        return f"({value})"

    def quote_startswith(self, value):
        """Adds a wildcard to quoted value

        >>> self.quote_startswith(self, 'kendall')
        ... "'kendall%'"
        """
        value = value + '%'
        return self.quote_value(value)

    def quote_endswith(self, value):
        """Adds a wildcard to quoted value

        >>> self.quote_endswith(self, 'kendall')
        ... "'%kendall'"
        """
        value = '%' + value
        return self.quote_value(value)

    def quote_like(self, value):
        """Adds a wildcard to quoted value

        >>> self.quote_like(self, 'kendall')
        ... "'%kendall%'"
        """
        value = f'%{value}%'
        return self.quote_value(value)

    def dict_to_sql(self, data, quote_values=True):
        """Convert a values nested into a dictionnary
        to a sql usable values. The values are quoted
        by default before being returned

        >>> self.dict_to_sql({'name__eq': 'Kendall'})
        ... (['name'], ["'Kendall'"])
        """
        fields = list(data.keys())
        if quote_values:
            quoted_value = list(
                map(lambda x: self.quote_value(x), data.values()))
            return fields, quoted_value
        else:
            return fields, data.values()

    def build_script(self, *sqls):
        return '\n'.join(map(lambda x: self.finalize_sql(x), sqls))

    def decompose_filters(self, **kwargs):
        """Decompose a set of filters to a list of
        key, operator and value list

        >>> self.decompose_filters({'rowid__eq': '1'})
        ... [('rowid', '=', '1')]
        """
        base_filters = {
            'eq': '=',
            'lt': '<',
            'gt': '>',
            'lte': '<=',
            'gte': '>=',
            'contains': 'like',
            'startswith': 'startswith',
            'endswith': 'endswith',
            'range': 'between',
            'ne': '!=',
            'in': 'in',
            'isnull': 'isnull'
        }
        filters_map = []
        for key, value in kwargs.items():
            if '__' not in key:
                key = f'{key}__eq'

            tokens = key.split('__', maxsplit=1)
            if len(tokens) > 2:
                raise ValueError(f'Filter is not valid. Got: {key}')

            lhv, rhv = tokens
            operator = base_filters.get(rhv)
            if operator is None:
                raise ValueError(
                    f'Operator is not recognized. Got: {key}'
                )
            filters_map.append((lhv, operator, value))
        return filters_map

    def build_filters(self, items):
        """Tranform a list of decomposed filters to
        be usable conditions in an sql statement

        >>> self.build_filters([('rowid', '=', '1')])
        ... ["rowid = '1'"]

        >>> self.build_filters([('rowid', 'startswith', '1')])
        ... ["rowid like '1%'"]


        >>> self.build_filters([('url', '=', Lower('url')])
        ... ["lower(url)"]
        """
        built_filters = []
        for item in items:
            field, operator, value = item

            if operator == 'in':
                if not isinstance(value, (tuple, list)):
                    raise ValueError(
                        'The value when using "in" should be a tuple or a list')

                quoted_list_values = (self.quote_value(item) for item in value)
                operator_and_value = self.IN.format_map({
                    'field': field,
                    'values': self.comma_join(quoted_list_values)
                })
                built_filters.append(operator_and_value)
                continue

            if operator == 'like':
                operator_and_value = self.LIKE.format_map({
                    'field': field,
                    'conditions': self.quote_like(value)
                })
                built_filters.append(operator_and_value)
                continue

            if operator == 'startswith':
                operator_and_value = self.LIKE.format_map({
                    'field': field,
                    'conditions': self.quote_startswith(value)
                })
                built_filters.append(operator_and_value)
                continue

            if operator == 'endswith':
                operator_and_value = self.LIKE.format_map({
                    'field': field,
                    'conditions': self.quote_endswith(value)
                })
                built_filters.append(operator_and_value)
                continue

            if operator == 'between':
                lhv, rhv = value
                operator_and_value = self.BETWEEN.format_map({
                    'field': field,
                    'lhv': lhv,
                    'rhv': rhv
                })
                built_filters.append(operator_and_value)
                continue

            if operator == 'isnull':
                if value:
                    operator_and_value = f'{field} is null'
                else:
                    operator_and_value = f'{field} is not null'
                built_filters.append(operator_and_value)
                continue

            value = self.quote_value(value)
            built_filters.append(
                self.simple_join((field, operator, value))
            )
        return built_filters

    def build_annotation(self, **conditions):
        function_filters = {}
        for key, function in conditions.items():
            if isinstance(function, Functions):
                function.backend = self
                # Use key as alias instead of column named
                # "lower(value)" in the returned results
                function_filters[key] = self.simple_join(
                    [function.function_sql(), f'as {key}']
                )

        joined_fields = self.comma_join(function_filters.values())
        return [joined_fields]
    

class SQLiteBackend(SQL):
    """Class that initiates and encapsulates a
    new connection to the database"""

    def __init__(self, database_name=None, table=None):
        if database_name is None:
            database_name = ':memory:'
        else:
            database_name = f'{database_name}.sqlite'
        self.database_name = database_name

        connection = sqlite3.connect(database_name)
        # connection.create_function('hash', 1, Hash())
        # connection.row_factory = BaseRow
        connection.row_factory = row_factory(self)
        self.connection = connection
        self.table = table

    def list_table_columns_sql(self, table):
        sql = f'pragma table_info({table.name})'
        query = Query(self, [sql], table=table)
        query.run()
        return query.result_cache

    def drop_indexes_sql(self, row):
        sql = self.DROP_INDEX.format_map({
            'value': row['name']
        })
        return sql

    def create_table_fields(self, table, columns_to_create):
        field_params = []
        if columns_to_create:
            while columns_to_create:
                column_to_create = columns_to_create.pop()
                field = table.fields_map[column_to_create]
                field_params.append(field.field_parameters())

            statements = [self.simple_join(param) for param in field_params]
            for i, statement in enumerate(statements):
                if i > 1:
                    statement = f'add table {statement}'
                statements[i] = statement

            alter_sql = self.ALTER_TABLE.format_map({
                'table': table.name,
                'params': self.simple_join(statements)
            })
            query = Query(self, [alter_sql], table=table)
            query.run(commit=True)

    def list_tables_sql(self):
        sql = self.SELECT.format(
            fields=self.comma_join(['rowid', 'name']),
            table='sqlite_schema'
        )
        not_like_clause = self.NOT_LIKE.format(
            field='name',
            wildcard=self.quote_value('sqlite_%')
        )
        where_clause = self.WHERE_CLAUSE.format(
            params=self.simple_join([
                self.EQUALITY.format(
                    field='type',
                    value=self.quote_value('table')
                ),
                self.AND.format(rhv=not_like_clause)
            ])
        )
        query = Query(self, [sql, where_clause])
        query.run()
        return query.result_cache

    def list_database_indexes(self):
        base_fields = ['type', 'name', 'tbl_name', 'sql']
        select_sql = self.SELECT.format_map({
            'fields': self.comma_join(base_fields),
            'table': 'sqlite_master'
        })
        where_clause = self.WHERE_CLAUSE.format_map({
            'params': self.EQUALITY.format_map({
                'field': 'type',
                'value': self.quote_value('index')
            })
        })
        sql = [select_sql, where_clause]
        query = Query(self, sql)
        query.run()
        return query.result_cache

    def list_table_indexes(self, table):
        sql = f'PRAGMA index_list({self.quote_value(table.name)})'
        query = Query(self, sql, table=table)
        query.run()
        return query.result_cache
    
    def save_row(self, row, updated_values):
        if not isinstance(row, BaseRow):
            raise ValueError()
        
        if row._marked_for_update:
            # TODO: Pass the current table somewhere
            # either in the row or [...]
            update_sql = self.UPDATE.format_map({
                'table': 'seen_urls',
                'params': self.EQUALITY.format_map({
                    'field': updated_values[0],
                    'value': self.quote_value(updated_values[1])
                })
            })
            where_clause = self.WHERE_CLAUSE.format_map({
                'params': self.EQUALITY.format_map({
                    'field': 'rowid',
                    'value': row['rowid']
                })
            })
            sql = [update_sql, where_clause]

            query = Query(self, sql, table=None)
            query.run(commit=True)
        return row
        
    # def delete(self):
    #     backend = self.initialize_backend
    #     delete_sql = backend.DELETE.format(table='')
    #     where_clause = backend.WHERE_CLAUSE.format_map({
    #         'params': backend.EQUALITY.format_map({
    #             'lhv': 'rowid',
    #             'rhv': self['rowid']
    #         })
    #     })
    #     sql = [delete_sql, where_clause]
    #     query = Query(backend, sql, table=None)
    #     query.run(commit=True)
