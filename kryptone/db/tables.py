from collections import OrderedDict, namedtuple

from kryptone.db.backends import SQLiteBackend
from kryptone.db.exceptions import ImproperlyConfiguredError
from kryptone.db.fields import AutoField, Field
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

    def __init__(self, database_name=None, inline_build=False):
        self.backend = None
        self.is_prepared = False
        if inline_build:
            self.backend = self.backend_class(
                database_name=database_name,
                table=self
            )

    def __hash__(self):
        return hash((self.name))

    def __eq__(self, value):
        return self.name == value

    def validate_values(self, fields, values):
        """Validate an incoming value in regards
        to the related field the user is trying
        to set on the column. The returned values
        are quoted by default"""
        validates_values = []
        for i, field in enumerate(fields):
            if field == 'rowid' or field == 'id':
                continue

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

    def bulk_create(self, objs):
        new_objects = []

        # Use a namedtuple to ensure that the values
        # that are entered match the fields on the
        # database. In other words, the data entered
        # always matches the fields of the database
        true_field_names = list(
            filter(lambda x: x != 'rowid', self.field_names))
        defaults = [None] * len(true_field_names)
        item = namedtuple(self.name, true_field_names, defaults=defaults)

        for obj in objs:
            if isinstance(obj, dict):
                new_objects.append(item(**obj))

            # https://stackoverflow.com/questions/2166818/how-to-check-if-an-object-is-an-instance-of-a-namedtuple
            if hasattr(obj, '_fields'):
                new_objects.append(obj)

        new_item = {}
        for obj in new_objects:
            for field in obj._fields:
                new_item[field] = getattr(obj, field)
            self.create(**new_item)

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

        # TODO: Create a query and only run it when
        # we need with QuerySet for the other functions
        query = Query(self.backend, [sql], table=self)
        query._table = self
        # query.run()
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

    def __init__(self, name, *, database_name=None, inline_build=False, fields=[], index=[], constraints=[]):
        self.name = name
        self.indexes = index
        self.constraints = constraints
        self.inline_build = inline_build
        super().__init__(
            database_name=database_name,
            inline_build=inline_build
        )
        self.fields_map = OrderedDict()

        for field in fields:
            if not isinstance(field, Field):
                raise ValueError(f'{field} should be an instance of Field')

            field.prepare(self)
            self.fields_map[field.name] = field

        # Automatically create an ID field
        self.fields_map['id'] = AutoField()

        field_names = list(self.fields_map.keys())
        field_names.append('rowid')
        self.field_names = field_names

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.name}>'

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
        """Returns the paramaters for all
        the fields present on the table"""
        return [
            field.field_parameters()
            for field in self.fields_map.values()
        ]

    def prepare(self):
        """Prepares and creates a table for
        the database"""
        if not self.inline_build and self.backend is None:
            message = (
                "Calling the Table class outside of Database "
                "requires that you set 'inline_build' to True"
            )
            raise ImproperlyConfiguredError(self, message)

        field_params = self.build_field_parameters()
        field_params = [
            self.backend.simple_join(params)
            for params in field_params
        ]
        sql = self.create_table_sql(self.backend.comma_join(field_params))
        query = self.query_class(self.backend, sql, table=self)
        query.run(commit=True)
        self.is_prepared = True


class DatabaseManager:
    """A manager is a class that implements query
    functionnalities for inserting, updating, deleting
    or retrieving data from the underlying database tables"""

    def __init__(self):
        self.table_map = {}

    def __get__(self, instance, cls=None):
        if not self.table_map:
            self.table_map = instance.table_map
        return self

    def first(self, table):
        """Returns the first row from
        a database table"""
        result = self.all(table)
        return result[0]

    def last(self, table):
        """Returns the last row from
        a database table"""
        result = self.all(table)
        return result[-1]

    def all(self, table):
        selected_table = self.table_map[table]
        all_sql = selected_table.backend.SELECT.format_map({
            'fields': selected_table.backend.comma_join(['rowid', '*']),
            'table': selected_table.name
        })
        sql = [all_sql]
        query = selected_table.query_class(
            selected_table.backend,
            sql,
            table=selected_table
        )
        query._table = selected_table
        query.run()
        return query.result_cache

    def create(self, table, **kwargs):
        """Creates a new row in the table of 
        the current database

        >>> database.objects.create('table_name', name='Kendall')
        """
        selected_table = self.table_map[table]
        fields, values = selected_table.backend.dict_to_sql(
            kwargs, quote_values=False)
        values = selected_table.validate_values(fields, values)

        joined_fields = selected_table.backend.comma_join(fields)
        joined_values = selected_table.backend.comma_join(values)
        sql = selected_table.backend.INSERT.format(
            table=selected_table.name,
            fields=joined_fields,
            values=joined_values
        )
        query = selected_table.query_class(
            selected_table.backend,
            [sql],
            table=selected_table
        )
        query.run(commit=True)
        return self.last(selected_table.name)

    def filter(self, table, **kwargs):
        """Filter the data in the database based on
        a set of criteria

        >>> database.objects.filter(name='Kendall')
        ... database.objects.filter(name__eq='Kendall')
        ... database.objects.filter(age__gt=15)
        ... database.objects.filter(name__in=['Kendall'])
        """
        selected_table = self.table_map[table]
        tokens = selected_table.backend.decompose_filters(**kwargs)
        filters = selected_table.backend.build_filters(tokens)

        if len(filters) > 1:
            filters = [' and '.join(filters)]

        select_sql = selected_table.backend.SELECT.format_map({
            'fields': selected_table.backend.comma_join(['rowid', '*']),
            'table': selected_table.name,
        })
        where_clause = selected_table.backend.WHERE_CLAUSE.format_map({
            'params': selected_table.backend.comma_join(filters)
        })
        sql = [select_sql, where_clause]
        query = selected_table.query_class(
            selected_table.backend, 
            sql, 
            table=selected_table
        )
        query.run()
        return query.result_cache
    
    def get(self, table, **kwargs):
        """Returns a specific row from the database
        based on a set of criteria

        >>> instance.objects.get('table_name', id__eq=1)
        ... instance.objects.get('table_name', id=1)
        """
        selected_table = self.table_map[table]
        base_return_fields = ['rowid', '*']
        filters = selected_table.backend.build_filters(
            selected_table.backend.decompose_filters(**kwargs)
        )

        # Functions SQL: select rowid, *, lower(url) from table
        select_sql = selected_table.backend.SELECT.format_map({
            'fields': selected_table.backend.comma_join(base_return_fields),
            'table': selected_table.name
        })
        sql = [select_sql]

        # Filters SQL: select rowid, * from table where url='http://'
        joined_statements = ' and '.join(filters)
        where_clause = selected_table.backend.WHERE_CLAUSE.format_map({
            'params': joined_statements
        })
        sql.extend([where_clause])

        query = selected_table.query_class(
            selected_table.backend, 
            sql, 
            table=selected_table
        )
        query.run()

        if not query.result_cache:
            return None

        if len(query.result_cache) > 1:
            raise ValueError('Returned more than 1 value')

        return query.result_cache[0]

    def annotate(self, table, **kwargs):
        """Annotations implements the usage of
        functions in the query

        For example, if we want the iteration of each
        value in the database to be returned in lowercase
        or in uppercase

        >>> instance.objects.annotate(lowered_name=Lower('name'))
        ... instance.objects.annotate(uppered_name=Upper('name'))

        If we want to return only the year section of a date

        >>> self.annotate(year=ExtractYear('created_on'))
        """
        selected_table = self.table_map[table]
        base_return_fields = ['rowid', '*']
        fields = selected_table.backend.build_annotation(**kwargs)
        base_return_fields.extend(fields)
        selected_table.field_names = selected_table.field_names + list(kwargs.keys())

        sql = selected_table.backend.SELECT.format_map({
            'fields': selected_table.backend.comma_join(base_return_fields),
            'table': selected_table.name
        })

        # TODO: Create a query and only run it when
        # we need with QuerySet for the other functions
        query = Query(
            selected_table.backend, 
            [sql], 
            table=selected_table
        )
        # query.run()
        # return query.result_cache
        return QuerySet(query)

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
    objects = DatabaseManager()

    def __init__(self, name, *tables):
        self.database_name = name
        self.migrations = self.migrations_class(database_name=name)

        self.table_map = {}
        for table in tables:
            if not isinstance(table, Table):
                raise ValueError('Value should be an instance of Table')

            if table.backend is None:
                table.backend = table.backend_class(
                    database_name=self.database_name,
                    table=table
                )
            self.table_map[table.name] = table

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
        self.migrations.make_migrations(self.table_instances)

    def migrate(self):
        """Implements the changes to the migration
        file into the SQLite database"""
        self.migrations.check(self.table_map)
