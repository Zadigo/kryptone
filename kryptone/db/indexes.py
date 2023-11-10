class Index:
    prefix = 'idx'

    def __init__(self, name, *fields):
        self.index_name = f'{self.prefix}_{name}'
        self._fields = list(fields)
        self._backend = None

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.index_name}>'

    def function_sql(self):
        sql = self._backend.CREATE_INDEX.format_map({
            'name': self.index_name,
            'table': 'seen_urls',
            'fields': self._backend.comma_join(self._fields)
        })
        return sql
