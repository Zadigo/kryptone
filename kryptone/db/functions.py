class Functions:
    def __init__(self, field_name):
        self.field_name = field_name
        self.backend = None

    def __str__(self):
        return f'<{self.__class__.__name__}({self.field_name})>'

    def function_sql(self):
        pass


class Lower(Functions):
    """Returns each values of the given
    column in lowercase
    
    >>> table.annotate(lowered_url=Lower('url'))
    """

    def function_sql(self):
        sql = self.backend.LOWER.format_map({
            'field': self.field_name
        })
        return sql


class Upper(Lower):
    """Returns each values of the given
    column in uppercase
    
    >>> table.annotate(url_upper=Upper('url'))
    """

    def function_sql(self):
        sql = self.backend.UPPER.format_map({
            'field': self.field_name
        })
        return sql


class Length(Functions):
    """Returns length of each iterated values
    from the database
    
    >>> table.annotate(url_length=Length('url'))
    """

    def function_sql(self):
        sql = self.backend.LENGTH.format_map({
            'field': self.field_name
        })
        return sql


class Max(Functions):
    """Returns the max value of a given
    column. """
    def function_sql(self):
        # sql = self.backend.MAX.format_map({
        #     'field': self.field_name
        # })
        # return sql

        # select rowid, *
        # from seen_urls
        # where rowid = (select max(rowid) from seen_urls)
        select_clause = self.backend.SELECT.format_map({
            'fields': self.backend.comma_join(['rowid', '*']),
            'table': self.backend.table.name
        })
        subquery_clause = self.backend.SELECT.format_map({
            'fields': self.backend.MAX.format_map({'field': self.field_name}),
            'table': self.backend.table.name
        })
        where_condition = self.backend.EQUALITY.format_map({
            'field': self.field_name,
            'value': self.backend.wrap_parenthentis(subquery_clause)
        })
        where_clause = self.backend.WHERE_CLAUSE.format_map({
            'params': where_condition
        })
        return self.backend.simple_join([select_clause, where_clause])


class Min(Functions):
    """Returns the max value of a given
    column. """
    def function_sql(self):
        select_clause = self.backend.SELECT.format_map({
            'fields': self.backend.comma_join(['rowid', '*']),
            'table': self.backend.table.name
        })
        subquery_clause = self.backend.SELECT.format_map({
            'fields': self.backend.MIN.format_map({'field': self.field_name}),
            'table': self.backend.table.name
        })
        where_condition = self.backend.EQUALITY.format_map({
            'field': self.field_name,
            'value': self.backend.wrap_parenthentis(subquery_clause)
        })
        where_clause = self.backend.WHERE_CLAUSE.format_map({
            'params': where_condition
        })
        return self.backend.simple_join([select_clause, where_clause])


class ExtractYear(Functions):
    """Extracts the year section of each
    iterated value
    
    We can annotate a row  with a value

    >>> table.annotate(year=ExtractYear('created_on'))

    Or filter data based on the return value of the function

    >>> table.filter(year__gte=ExtractYear('created_on'))
    """
    def function_sql(self):
        sql = self.backend.STRFTIME.format_map({
            'format': self.backend.quote_value('%Y'),
            'value': self.field_name
        })
        return sql
