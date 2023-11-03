import datetime
import json
import secrets
from collections import defaultdict
from functools import cached_property

from kryptone.conf import settings
from kryptone.db import DATABASE
from kryptone.db.backends import SQLiteBackend
from kryptone.db.fields import Field
from kryptone.db.queries import Query


class Migrations:
    """Main class to manage the 
    `migrations.json` file"""

    CACHE = {}
    backend_class = SQLiteBackend

    def __init__(self):
        self.file = settings.PROJECT_PATH / 'migrations.json'
        self.CACHE = self.read_content
        self.file_id = self.CACHE['id']

        try:
            self.tables = self.CACHE['tables']
        except KeyError:
            raise KeyError('Migration file is not valid')
        self.migration_table_map = [table['name'] for table in self.tables]
        self.fields_map = defaultdict(list)

        self.tables_for_creation = set()
        self.tables_for_deletion = set()
        self.existing_tables = set()
        self.has_migrations = False

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.file_id}]>'

    @cached_property
    def read_content(self):
        try:
            with open(self.file, mode='r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create a blank migration file
            return self.blank_migration()

    def _write_fields(self, table):
        fields_map = []
        for name, field in table.fields_map.items():
            field_name, params = list(field.deconstruct())
            fields_map.append({
                'name': field_name,
                'params': params
            })
        self.fields_map[table.name] = fields_map

    def _write_indexes(self, table):
        indexes = {}
        for index in table.indexes:
            indexes[index.index_name] = index._fields
        return indexes
    
    def create_migration_table(self):
        from kryptone.db.tables import Table
        table_fields = [
            Field('name'),
            Field('applied')
        ]
        table = Table('migrations', '', fields=table_fields)
        table.prepare()

    def check(self, table_instances={}):
        from kryptone.db.tables import Table

        errors = []
        for name, table_instance in table_instances.items():
            if not isinstance(table_instance, Table):
                errors.append(
                    f"Value should be instance "
                    f"of Table. Got: {table_instance}"
                )

        if errors:
            raise ValueError(*errors)
        
        if not table_instances:
            return

        backend = self.backend_class(database_name=DATABASE)
        database_tables = backend.list_tables_sql()
        # When the table is in the migration file
        # and not in the database, it needs to be
        # created
        for table_name in self.migration_table_map:
            table_exists = not any(
                map(lambda x: x['name'] == table_name, database_tables))
            if table_exists:
                self.tables_for_creation.add(table_name)

        # When the table is not in the migration
        # file but present in the database
        # it needs to be deleted
        for database_row in database_tables:
            if database_row['name'] not in self.migration_table_map:
                self.tables_for_deletion.add(database_row)

        sqls_to_run = []

        if self.tables_for_creation:
            for table_name in self.tables_for_creation:
                table = table_instances.get(table_name, None)
                if table is None:
                    continue

                table.prepare()
            self.has_migrations = True

        if self.tables_for_deletion:
            sql_script = []
            for database_row in self.tables_for_deletion:
                sql = self.backend_class.DROP_TABLE.format(
                    table=database_row['name']
                )
                sql_script.append(sql)
            sql = backend.build_script(*sql_script)
            sqls_to_run.append(sql)
            self.has_migrations = True

        # For existing tables, check that the
        # fields are the same and well set as
        # indicated in the migration file
        for database_row in database_tables:
            if (database_row['name'] in self.tables_for_creation or
                    database_row['name'] in self.tables_for_deletion):
                continue

            table_instance = table_instances.get(database_row['name'], None)
            if table_instance is None:
                continue

            self.check_fields(table_instances[database_row['name']], backend)

        Query.run_script(backend, sqls_to_run)
        # self.migrate(table_instances)

        # Create indexes for each table
        database_indexes = backend.list_database_indexes()
        index_sqls = []
        for name, table in table_instances.items():
            # if name in database_indexes:
            #     raise ValueError('Index already exists on databas')

            for index in table.indexes:
                index._backend = backend
                index_sqls.append(index.function_sql())

        # Remove obsolete indexes
        for database_index in database_indexes:
            if database_index not in table.indexes:
                index_sqls.append(backend.drop_indexes_sql(database_index))

        # Create table constraints
        # table_constraints = []
        # for _, table in table_instances.items():
        #     for field in table.fields:
        #         constraints = [constraint.as_sql() for constraint in field.base_constraints]
        #         sql_clause = backend.CHECK_CONSTRAINT.format_map({
        #             'conditions': backend.operator_join(constraints)
        #         })
        #         table_constraints.append(sql_clause)

        # Query.run_multiple(backend, index_sqls)

        self.tables_for_creation.clear()
        self.tables_for_deletion.clear()
        backend.connection.close()

    def check_fields(self, table, backend):
        """Checks the migration file for fields
        in relationship with the table"""
        database_table_columns = backend.list_table_columns_sql(table)

        columns_to_create = set()
        for field_name in table.fields_map.keys():
            if field_name not in database_table_columns:
                columns_to_create.add(field_name)

        # TODO: Drop columns that were dropped in the database

        backend.create_table_fields(table, columns_to_create)

    def blank_migration(self):
        """Creates a blank initial migration file"""
        migration_content = {}

        file_path = settings.PROJECT_PATH / 'migrations.json'
        if not file_path.exists():
            file_path.touch()
        
        with open(file_path, mode='w') as f:
            migration_content['id'] = secrets.token_hex(5)
            migration_content['date'] = str(datetime.datetime.now())
            migration_content['number'] = 1

            migration_content['tables'] = []
            json.dump(migration_content, f, indent=4, ensure_ascii=False)
            return migration_content

    def make_migrations(self, tables):
        # Write to the migrations.json file only if
        # necessary e.g. dropped tables, changed fields
        if self.has_migrations:
            cache_copy = self.CACHE.copy()
            with open(settings.PROJECT_PATH / 'migrations.json', mode='w+') as f:
                cache_copy['id'] = secrets.token_hex(5)
                cache_copy['date'] = str(datetime.datetime.now())
                cache_copy['number'] = self.CACHE['number'] + 1

                cache_copy['tables'] = []
                for table in tables:
                    self._write_fields(table)
                    cache_copy['tables'].append({
                        'name': table.name,
                        'fields': self.fields_map[table.name],
                        'indexes': self._write_indexes(table)
                    })
                json.dump(cache_copy, f, indent=4, ensure_ascii=False)

    def get_table_fields(self, name):
        table_index = self.table_map.index(name)
        return self.tables[table_index]['fields']

    def reconstruct_table_fields(self, table):
        reconstructed_fields = []
        fields = self.get_table_fields(table)
        for field in fields:
            instance = Field.create(
                field['name'],
                field['params'],
                verbose_name=field['verbose_name']
            )
            reconstructed_fields.append(instance)
        return reconstructed_fields
