class Functions:
    def __init__(self, field):
        self.field_name = field
        self.backend = None

    def function_sql(self):
        pass


class Lower(Functions):
    """Returns each values of the given
    column in lowercase
    
    >>> table.annotate(url_lower=Lower('url'))
    """

    def __str__(self):
        return f'<{self.__class__.__name__}({self.field_name})>'

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
