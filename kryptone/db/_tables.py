from kryptone.db.fields import CharField
from kryptone.db.tables import Table


table = Table('single_table', inline_build=True, fields=[
    CharField('name')
])
table.prepare()
table.create(name='Kendall')
v = table.first()
print(table)
