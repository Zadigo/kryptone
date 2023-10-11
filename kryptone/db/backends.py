import sqlite3
from collections import OrderedDict, defaultdict
import pandas


class Field:
    def __init__(self, name, *, null=False, primary_key=False):
        self.is_primary_key = primary_key
        self.name = name
        self.null = null

    def __repr__(self):
        return f'<{self.__class__.__name__} "{self.name}">'

    def prepare(self):
        field_parameters = ['text', 'not null']

        if self.is_primary_key:
            field_parameters.append('primary key')

        if self.null:
            field_parameters.append('null')
        else:
            field_parameters.pop(field_parameters.index('not null'))
            field_parameters.append('null')
        return ' '.join(field_parameters)


class Index:
    def __init__(self, name, field):
        self.name = f'idx_{name}'
        self.field = field
        self.table = None

    def as_sql(self):
        return [self.name, self.table, self.field]


class SQL:
    """Base SQL statement builder"""

    ALTER_TABLE = 'alter table {table} add column {field_name} {field_params}'
    CREATE_TABLE = 'create table if not exists {table} ({params})'
    CREATE_INDEX = 'create unique index {index_name} on {table} ({fields})'
    CREATE = 'insert into {table} ({fields}) values({values})'
    DELETE = 'delete from {table}'
    INSERT = 'INSERT INTO {table} ({field}) VALUES({values})'
    LIMIT = 'limit {value}'
    ORDER_BY = 'order by {field} {ordering}'
    SELECT = 'select {fields} from {table}'
    UPDATE = 'update {table} set {field}={new_value} where {field}={value}'
    WHERE_CLAUSE = 'where {params}'

    AND = 'and {rhv}'
    OR = 'or {rhv}'

    EQUALITY = '{field}={value}'
    CONTAINS = '{field} in ({values})'
    WILD_CARD = '{field} like {wildcard}'
    BETWEEN = '{field} between {lhv} and {rhv}'
    NOT_LIKE = '{field} not like {wildcard}'

    COUNT = 'count({field})'

    def finalize_sql(self, sql):
        """Checks that the SQL to be 
        used ends with a `;`"""
        if sql.endswith(';'):
            return sql
        return f'{sql};'

    def quote(self, value):
        """Ensures that text values are
        correctly quoted

        >>> self.quote('Kendall')
        ... "'Kendall'"
        """
        if isinstance(value, int):
            return value

        if value.startswith("'"):
            return value
        return f"'{value}'"

    def join(self, values):
        """Joins a set of values 
        using a comma"""
        return ', '.join(values)

    def join_tokens(self, *sqls):
        return ' '.join(sqls)

    def dict_to_sql(self, data):
        fields = list(data.keys())
        values = list(map(lambda x: self.quote(x), data.values()))
        return fields, values

    def complex_dict_to_sql(self, data):
        """Converts operates as `age__gt=15` to
        a python readable list `[['age', '>', 15]]`"""
        operators = {
            'gt': '>',
            'gte': '>=',
            'lt': '<',
            'lte': '<=',
            'eq': '='
        }
        base_operators = list(operators.keys())
        tokens = []
        for key, value in data.items():
            if '__' in key:
                lhv, rhv = key.split('__')
                if rhv not in base_operators:
                    raise ValueError('Operator is not valid')
                tokens.append([lhv, operators[rhv], self.quote(value)])
            else:
                tokens.append([key, operators['eq'], self.quote(value)])
        return tokens

    def construct_sql_tokens(self, tokens):
        return self.finalize_sql(' '.join(tokens))

    def data_to_dict(self, data):
        pass

    def data_to_dataframe(self, data):
        return pandas.DataFrame(data=self.data_to_dict(data))

    def build_script(self, *sqls):
        script = '\n'.join(map(lambda x: self.finalize_sql(x), sqls))
        return script


class SQliteBackend(SQL):
    """Base backend for the SQLite database"""

    def __init__(self, database=None):
        self.database = f'{database}.sqlite' or ':memory:'
        connection = sqlite3.connect(self.database)
        self.connection = connection
        # self.connection.row_factory = sqlite3.Row

    def __getitem__(self, key):
        sql = self.finalize_sql(
            self.SELECT.format(fields=key, table=self.name, params='key=?')
        )
        result = self.connection.execute(sql)
        if not result:
            raise KeyError()
        return list(result)

    def __setitem__(self, key, value):
        sql = self.finalize_sql(
            self.INSERT.format(
                table=self.name,
                field=key,
                columns=key,
                values=self.quote(value)
            )
        )
        print(sql)
        result = self.connection.execute(sql)
        self.connection.commit()

    def __delitem__(self, key):
        pass

    def __len__(self):
        count_sql = self.COUNT.format(field='*')
        sql = self.SELECT.format(fields=count_sql, table='seen_urls')
        sql = self.finalize_sql(sql)
        print(list(self.connection.execute(sql))[0][-1])
        return list(self.connection.execute(sql))[0][-1]

    def __iter__(self):
        pass

    def __enter__(self, *args, **kwargs):
        pass

    def __exit__(self):
        pass

    def __del__(self):
        pass

    def keys(self):
        pass

    def values(self):
        pass

    def items(self):
        pass

    def order_by_sql(self, field, ordering):
        ordering_types = ['ASC', 'DESC']
        if ordering not in ordering_types:
            raise ValueError('Ordering type if not correct')
        return self.ORDER_BY.format(field=field, ordering=ordering)

    def limit_sql(self, value):
        if not isinstance(value, int):
            raise ValueError('Limit should be an integer')
        return [self.LIMIT.format(value=value)]

    def list_tables(self):
        sql = self.SELECT.format(fields='name', table='sqlite_schema')
        # self.EQUALITY.format(field='type', value=self.quote('table'))

        not_like_clause = self.NOT_LIKE.format(
            field='name',
            wildcard=self.quote('sqlite_%')
        )

        rhv = [
            self.EQUALITY.format(field='type', value=self.quote('table')),
            self.AND.format(rhv=not_like_clause)
        ]
        rhv = self.join_tokens(*rhv)
        where_clause = self.WHERE_CLAUSE.format(params=rhv)
        sql = self.join_tokens(sql, where_clause)
        sql = self.finalize_sql(sql)
        # print(sql)
        print(list(self.connection.execute(sql)))


# class Query:
#     def __init__(self, table, connection):
#         self._table = table
#         self._connection = connection
#         self._sql = None

#     def run_query(self):
#         if not isinstance(self._connection, sqlite3.Cursor):
#             raise ValueError()
#         self._connection.execute(self._sql)


class QuerySet:
    def __init__(self, table, query):
        self.table = table
        self.query = query


class Table(SQliteBackend):
    """Base SQLite table"""

    fields = OrderedDict()
    index_map = OrderedDict()

    def __init__(self, name, *, fields=[], indexes=[]):
        super().__init__(database='my_database')

        for field in fields:
            if not isinstance(field, Field):
                raise ValueError()
            self.fields[field.name] = field

        self.name = name
        self.connection.execute(self.create_table_sql())
        self.connection.commit()

        new_fields = []
        for field in fields:
            truth_array = any(
                map(lambda x: field.name in x, self.table_fields)
            )
            if truth_array:
                continue
            new_fields.append(field)

        sqls = []
        for field in new_fields:
            sql = self.ALTER_TABLE.format(
                table=self.name,
                field_name=field.name,
                field_params=field.prepare()
            )
            sqls.append(sql)

        if sqls:
            sql = self.build_script(*sqls)
            self.connection.executescript(sql)
            self.connection.commit()

        if indexes:
            indexes_sql = []
            # for index in indexes:
            #     if not isinstance(index, Index):
            #         raise ValueError()
            #     index.table = self
            #     self.index_map[index.name] = index
            #     indexes_sql.append(self.CREATE_INDEX.format(
            #         index_name=index.name,
            #         table=self.name,
            #         fields=index.field
            #     ))
            # sqls = list(map(lambda x: self.finalize_sql(x), indexes_sql))
            # self.connection.execute(sqls[0])
        else:
            pass

        self.connection.commit()

    @property
    def table_fields(self):
        """Returns the current fields present
        in the database"""
        # return list(self.fields.keys())
        sql = f'pragma table_info({self.name})'
        return list(self.connection.execute(self.finalize_sql(sql)))

    @property
    def table_indexes(self):
        select_clause = self.SELECT.format(
            fields=self.join(['name', 'tbl_name']),
            table='sqlite_master'
        )
        where_clause = self.WHERE_CLAUSE.format(
            params=self.EQUALITY.format(
                field='type', value=self.quote('index'))
        )
        sql = self.join_tokens(select_clause, where_clause)
        print(list(self.connection.execute(self.finalize_sql(sql))))

    def create_table_sql(self):
        sql = self.CREATE_TABLE.format(
            table=self.name,
            # params='key integer primary key, url blob'
            params='id primary key, url blob'
        )
        return self.finalize_sql(sql)
    
    def drop_column_sql(self):
        temporary_name = 'googke'
        script = f"""
        PRAGMA foreign_keys=off;
        BEGIN TRANSACTION;

        CREATE TABLE IF NOT EXISTS {temporary_name}(column_definition);

        INSERT INTO {temporary_name}(column_list)
        SELECT column_list
        FROM table;

        DROP TABLE {self.name};

        ALTER TABLE {temporary_name} RENAME TO {self.name}; 

        COMMIT;
        PRAGMA foreign_keys=on;
        """

    def create_index_sql(self):
        pass

    def filter(self, **kwargs):
        tokens = self.complex_dict_to_sql(kwargs)
        if len(tokens) > 1:
            select_sql = self.SELECT.format(fields='*', table=self.name)
            where_sql = self.WHERE_CLAUSE.format(params=rhv[0])

            and_clauses = []
            for i, token in enumerate(tokens):
                if i == 0:
                    continue
                rhv = ''.join(token)
                and_clauses.append(self.AND.format(rhv=rhv))

            and_clauses = self.join(and_clauses)
            sql = self.join_tokens(select_sql, where_sql, and_clauses)
        else:
            select_sql = self.SELECT.format(fields='*', table=self.name)
            rhv = list(map(lambda x: ''.join(x), tokens))
            where_sql = self.WHERE_CLAUSE.format(params=rhv[0])
            sql = self.join_tokens(select_sql, where_sql)
        result = self.connection.execute(self.finalize_sql(sql))
        return list(result)

    def create(self, **kwargs):
        fields, values = self.dict_to_sql(kwargs)
        fields = self.join(fields)
        values = self.join(values)
        sql = self.CREATE.format(
            table=self.name,
            fields=fields,
            values=values
        )
        self.connection.execute(sql)
        self.connection.commit()

    def delete(self, **kwargs):
        pass

    def get(self, **kwargs):
        pass

    def all(self):
        sql = self.SELECT.format(table=self.name, fields='*')
        sql = self.finalize_sql(sql)
        data = self.connection.execute(sql)

        dict_data = []
        for row in data:
            element = {}
            for i, item in enumerate(row):
                element[self.table_fields[i]] = item
            dict_data.append(element)
        # print(dict_data)
        df = pandas.DataFrame(data=dict_data)
        print(df)
        return list(data)


# s = SQL()
# r = s.complex_dict_to_sql({'url__gt': 'Kendall'})
# b = ' '.join(r)
# print(b)

c = Table('seen_urls', fields=[Field('state'), Field('url')],
          indexes=[Index('seen_urls', 'url')])
# c['url'] = 'http://example.com/1'
# print(c['url'])

# c.update(id=1, url='http://exampl.com/1')
# c.create(url='http://google.com/kendall')
# print(c.filter(url='http://google.com/kendall/1'))
# print(len(c))
# c.all()
c.table_indexes
