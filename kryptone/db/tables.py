from collections import OrderedDict

from kryptone.db import DATABASE
from kryptone.db.backends import SQLiteBackend
from kryptone.db.fields import Field
from kryptone.db.migrations import Migrations
from kryptone.db.queries import Query, QuerySet


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

    def __init__(self, database_name=None):
        self.backend = self.backend_class(
            database_name=database_name or DATABASE,
            table=self
        )

    def __hash__(self):
        return hash((self.name))

    def validate_values(self, fields, values):
        """Validate an incoming value in regards
        to the related field the user is trying
        to set on the column. The returned values
        are quoted by default"""
        validates_values = []
        for i, field in enumerate(fields):
            field = self.fields_map[field]
            validated_value = self.backend.quote_value(
                field.to_database(list(values)[i])
            )
            validates_values.append(validated_value)
        return validates_values

    def all(self):
        all_sql = self.backend.SELECT.format_map({
            'fields': self.backend.comma_join(['rowid', '*']),
            'table': self.name
        })
        sql = [all_sql]
        query = self.query_class(self.backend, sql, table=self)
        query._table = self
        query.run()
        return query.result_cache
        # return QuerySet(query)

    def filter(self, **kwargs):
        """Filter the data in the database based on
        a set of criteria
        
        >>> self.filter(name='Kendall')
        ... self.filter(name__eq='Kendall')
        ... self.filter(age__gt=15)
        ... self.filter(name__in=['Kendall'])
        """
        tokens = self.backend.decompose_filters(**kwargs)
        filters = self.backend.build_filters(tokens)

        if len(filters) > 1:
            filters = [' and '.join(filters)]

        select_sql = self.backend.SELECT.format_map({
            'fields': self.backend.comma_join(['rowid', '*']),
            'table': self.name,
        })
        where_clause = self.backend.WHERE_CLAUSE.format_map({
            'params': self.backend.comma_join(filters)
        })
        sql = [select_sql, where_clause]
        query = self.query_class(self.backend, sql, table=self)
        query._table = self
        query.run()
        return query.result_cache

    def first(self):
        """Returns the first row from
        a database table"""
        result = self.all()
        return result[0]

    def last(self):
        """Returns the last row from
        a database table"""
        result = self.all()
        return result[-1]

    def create(self, **kwargs):
        """Creates a new row in the database table
        
        >>> self.create(name='Kendall')
        """
        fields, values = self.backend.dict_to_sql(kwargs, quote_values=False)
        values = self.validate_values(fields, values)

        joined_fields = self.backend.comma_join(fields)
        joined_values = self.backend.comma_join(values)
        sql = self.backend.INSERT.format(
            table=self.name,
            fields=joined_fields,
            values=joined_values
        )
        query = self.query_class(self.backend, [sql])
        query._table = self
        query.run(commit=True)
        return self.last()

    def get(self, **kwargs):
        """Returns a specific row from the database
        based on a set of criteria
        
        >>> self.get(id__eq=1)
        ... self.get(id=1)
        """
        base_return_fields = ['rowid', '*']
        filters = self.backend.build_filters(
            self.backend.decompose_filters(**kwargs)
        )

        # Functions SQL: select rowid, *, lower(url) from table
        select_sql = self.backend.SELECT.format_map({
            'fields': self.backend.comma_join(base_return_fields),
            'table': self.name
        })
        sql = [select_sql]

        # Filters SQL: select rowid, * from table where url='http://'
        joined_statements = ' and '.join(filters)
        where_clause = self.backend.WHERE_CLAUSE.format_map({
            'params': joined_statements
        })
        sql.extend([where_clause])

        query = self.query_class(self.backend, sql, table=self)
        query._table = self
        query.run()

        if not query.result_cache:
            return None

        if len(query.result_cache) > 1:
            raise ValueError('Returned more than 1 value')

        return query.result_cache[0]

    def annotate(self, **kwargs):
        """Annotations implements the usage of
        functions in the query
        
        For example, if we want the iteration of each
        value in the database to be returned in lowercase
        or in uppercase

        >>> self.annotate(lowered_name=Lower('name'))
        ... self.annotate(uppered_name=Upper('name'))

        If we want to return only the year section of a date
        
        >>> self.annotate(year=ExtractYear('created_on'))
        """
        base_return_fields = ['rowid', '*']
        fields = self.backend.build_annotation(**kwargs)
        base_return_fields.extend(fields)
        self.field_names = self.field_names + list(kwargs.keys())

        sql = self.backend.SELECT.format_map({
            'fields': self.backend.comma_join(base_return_fields),
            'table': self.name
        })

        query = Query(self.backend, [sql], table=self)
        query._table = self
        query.run()
        # return query.result_cache
        return QuerySet(query)
    
    def order_by(self, *fields):
        base_return_fields = ['rowid', '*']
        ascending_fields = set()
        descending_fields = set()

        for field in fields:
            if field.startswith('-'):
                descending_fields.add(field.removeprefix('-'))
                continue
            ascending_fields.add(field)

        sql = self.backend.SELECT.format_map({
            'fields': self.backend.comma_join(base_return_fields),
            'table': self.name
        })

        ascending_fields = [
            self.backend.ASCENDING.format(field=field)
            for field in ascending_fields
        ]
        descending_fields = [
            self.backend.DESCENDNIG.format(field=field)
            for field in descending_fields
        ]
        conditions = ascending_fields + descending_fields

        order_by_clause = self.backend.ORDER_BY.format_map({
            'conditions': self.backend.comma_join(conditions)
        })
        sql = [sql, order_by_clause]
        query = Query(self.backend, sql, table=self)
        query.run()
        return query.result_cache


class Table(AbstractTable):
    """Represents a table in the database. This class
    can be used independently but would require creating
    and managing table creation

    To create a table without using `Database`:

    >>> table = Table('my_table', 'my_database', fields=[Field('url')])
    ... table.prepare()
    ... table.create(url='http://example.come')

    However, if you wish to manage a migration file and other table related
    tasks, wrapping tables in `Database` is the best option:

    >>> table = Table('my_table', 'my_database', fields=[Field('url')])
    ... database = Database('my_database', table)
    ... database.make_migrations()
    ... database.migrate()
    ... table.create(url='http://example.com')
    """
    fields_map = OrderedDict()

    def __init__(self, name, *, database_name=None, fields=[], index=[], constraints=[]):
        self.name = name
        self.indexes = index
        self.constraints = constraints
        super().__init__(database_name=database_name)

        for field in fields:
            if not isinstance(field, Field):
                raise ValueError(f'{field} should be an instance of Field')

            field.prepare(self)
            self.fields_map[field.name] = field
        
        field_names = list(self.fields_map.keys())
        field_names.append('rowid')
        self.field_names = field_names

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.name}]>'

    def has_field(self, name):
        return name in self.fields_map

    def create_table_sql(self, fields):
        sql = self.backend.CREATE_TABLE.format_map({
            'table': self.name,
            'fields': fields
        })
        return [sql]

    def drop_table_sql(self, name):
        sql = self.backend.DROP_TABLE.format_map({
            'table': name
        })
        return [sql]

    def build_field_parameters(self):
        return [
            field.field_parameters()
            for field in self.fields_map.values()
        ]

    def prepare(self):
        """Prepares and creates a table for
        the database"""
        field_params = self.build_field_parameters()
        field_params = [
            self.backend.simple_join(params)
            for params in field_params
        ]
        sql = self.create_table_sql(self.backend.comma_join(field_params))
        query = self.query_class(self.backend, sql, table=self)
        query.run(commit=True)


class Database:
    """This class links and unifies independent
    tables together and allows the management of
    a migration file

    Creating a new database can be done by doing the following steps:

    >>> table = Table('my_table', 'my_database', fields=[Field('url')])
    ... database = Database('my_database', table)
    ... database.make_migrations()
    ... database.migrate()
    ... table.create(url='http://example.com')

    Connections to the database are opened at the table level.

    `make_migrations` writes the physical changes to the
    local tables into the `migrations.json` file

    `migrate` implements the changes to the migration
    file into the SQLite database
    """

    migrations = None
    migrations_class = Migrations

    def __init__(self, name, *tables):
        self.migrations = self.migrations_class()
        self.table_map = {}
        for table in tables:
            if not isinstance(table, Table):
                raise ValueError('Value should be an instance of Table')
            self.table_map[table.name] = table

        self.database_name = name
        self.table_instances = list(tables)

    def __repr__(self):
        tables = list(self.table_map.values())
        return f'<{self.__class__.__name__} {tables}>'

    def __getitem__(self, table_name):
        return self.table_map[table_name]

    def get_table(self, table_name):
        return self.table_map[table_name]

    def make_migrations(self):
        """Updates the migration file with the
        local changes to the tables. Make migrations
        should generally be called before running `migrate`
        """
        self.migrations.has_migrations = True
        self.migrations.migrate(self.table_instances)

    def migrate(self):
        """Implements the changes to the migration
        file into the SQLite database"""
        self.migrations.check(self.table_instances)
