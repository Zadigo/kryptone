import secrets

from kryptone.db.backends import SQLiteBackend


class CheckConstraint:
    def __init__(self, name, *, fields=[]):
        self.name = name
        self.fields = fields

    def __call__(self, value):
        pass


class MaxLengthConstraint(CheckConstraint):
    def __init__(self, fields=[]):
        super().__init__(
            name=f'cst_{secrets.token_bytes(nbytes=5)}', 
            fields=fields
        )
        self.max_length = None

    def __call__(self, value):
        if value is None:
            return True
        return len(value) > self.max_length

    def as_sql(self, backend):
        if not isinstance(backend, SQLiteBackend):
            raise ValueError()
        values = [
            backend.CONDITION.format_map({'field': field, 'operator': '>', 'value': self.max_length})
            for field in self.fields
        ]
        sql = backend.CHECK_CONSTRAINT.format_map({
            'constraints': backend.operator_join(values)
        })
        return sql
