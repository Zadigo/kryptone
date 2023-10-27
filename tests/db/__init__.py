
from kryptone.db.fields import Field
from kryptone.db.tables import Table


def create_table(create=False):
    table = Table('celebrities', 'test_database', fields=[
        Field('name')
    ])
    table.prepare()
    if create:
        table.create(name='Kendall Jenner')
    return table.backend
    