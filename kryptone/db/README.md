



# Creating a table

A table can be created either inline or with a cluster of tables using `Database`.

```python
from krytpone.db.tables import Table
from krytpone.db.fields import CharField

table = Table('my_table', database_name='my_database', inline_build=True, fields=[
    CharField('name')
])
table.prepare()
```

The above will create a single table called `my_table` in the `my_database` sqlite database and with the a column called `name`.

By default, when calling the `Table` instance, a connection will is not automatically established with sqlite. You need to set the `inline_build` to True and then call `prepare` to run the table creation sequence.

In order to manage multiple tables in a database, using `Database` implements additional functionnalities such as migrations (or table state tracking).

```python
from krytpone.db.tables import Table
from krytpone.db.fields import CharField

table = Table('my_table', database_name='my_database', fields=[
    CharField('name')
])

database = Database('my_database', tables=[table])
database.makemigrations()
dataase.migrate()
table = database.get_table('my_table')
```

