
class Query:
    """This class represents an sql statement query
    and is responsible for executing the query on the
    database. The return data is stored on
    the `result_cache`
    """

    def __init__(self, backend, sql_tokens, table=None):
        self._table = table
        
        from kryptone.db.backends import SQLiteBackend
        if not isinstance(backend, SQLiteBackend):
            raise ValueError('Connection should be an instance SQLiteBackend')

        self._backend = backend
        self._sql = None
        self._sql_tokens = sql_tokens
        self.result_cache = []

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self._sql}]>'

    # def __del__(self):
    #     self._backend.connection.close()

    @classmethod
    def run_multiple(cls, backend, *sqls, **kwargs):
        """Runs multiple queries against the database"""
        for sql in sqls:
            instance = cls(backend, sql, **kwargs)
            instance.run(commit=True)
            yield instance

    @classmethod
    def create(cls, backend, sql_tokens, table=None):
        """Creates a new `Query` class to be executed"""
        return cls(backend, sql_tokens, table=table)

    def prepare_sql(self):
        """Prepares a statement before it is sent
        to the database by joining the sql statements
        and implement a `;` to the end

        >>> ["select url from seen_urls", "where url='http://'"]
        ... "select url from seen_urls where url='http://';"
        """
        sql = self._backend.simple_join(self._sql_tokens)
        self._sql = self._backend.finalize_sql(sql)

    def run(self, commit=False):
        """Runs an sql statement and stores the
        return data on the `result_cache`"""
        self.prepare_sql()
        result = self._backend.connection.execute(self._sql)
        if commit:
            self._backend.connection.commit()
        self.result_cache = list(result)


class QuerySet:
    def __init__(self, query):
        if not isinstance(query, Query):
            raise ValueError(f"{query} should be an instance of Query")
        
        self.query = query
        self.result_cache = []

    def __repr__(self):
        self.load_cache()
        return f'<{self.__class__.__name__} {self.result_cache}>'

    # def __str__(self):
    #     self.load_cache()
    #     return str(self.result_cache)

    def __iter__(self):
        self.load_cache()
        for item in self.result_cache:
            yield item

    def load_cache(self):
        if not self.result_cache:
            # TODO: Run the query only when the
            # queryset is evaluated as oppposed
            # to running it in the methods: filters etc.
            self.query.run()
            self.result_cache = self.query.result_cache

    def exclude(self, **kwargs):
        pass

    def order_by(self, *fields):
        ascending_fields = set()
        descending_fields = set()
        for field in fields:
            if field.startswith('-'):
                field = field.removeprefix('-')
                descending_fields.add(field)
            else:
                ascending_fields.add(field)
        previous_sql = self.query._backend.de_sqlize_statement(self.query._sql)
        ascending_statements = [
            self.query._backend.ASCENDING.format_map({'field': field})
            for field in ascending_fields
        ]
        descending_statements = [
            self.query._backend.DESCENDNIG.format_map({'field': field})
            for field in descending_fields
        ]
        final_statement = ascending_statements + descending_statements
        order_by_clause = self.query._backend.ORDER_BY.format_map({
            'conditions': self.query._backend.comma_join(final_statement)
        })
        sql = [previous_sql, order_by_clause]
        new_query = self.query.create(
            self.query._backend, 
            sql, 
            table=self.query._table
        )
        new_query.run()
        # return QuerySet(new_query)
        return new_query.result_cache

    def values(self, *fields):
        self.load_cache()
        return_values = []
        if not fields:
            fields = self.query._table.field_names

        for row in self.result_cache:
            result = {}
            for field in fields:
                result[field] = row[field]
            return_values.append(result)
        return return_values
