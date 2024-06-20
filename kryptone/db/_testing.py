import datetime
import pathlib
from collections import namedtuple
from kryptone.conf import settings
from kryptone.db import tables
from kryptone.db.fields import BooleanField, CharField, Field, JSONField
from kryptone.db.functions import ExtractYear, Lower, Max
from kryptone.db.migrations import Migrations
from kryptone.db.tables import Database, Table

# fields = [
#     CharField('url', max_length=500, unique=True),
#     BooleanField('visited', default=False),
#     Field('created_on')
# ]
# table = Table('something_urls', database_name='scraping', fields=fields)
# table.prepare()

setattr(settings, 'PROJECT_PATH', pathlib.Path('.'))

table1 = Table('url', fields=[
    CharField('url')
])
table2 = Table('business', fields=[
    CharField('name')
])
database = Database('my_database', table1, table2)
database.make_migrations()
database.migrate()
# print('New object', database.objects.create('url', url='http://google.com'))
# print('All', database.objects.all('url'))
# print('First', database.objects.first('url'))
# print('Last', database.objects.last('url'))
# print('Filter', database.objects.filter('url', id__eq=3))
# print('Get', database.objects.get('url', id__eq=1))
# print('Get', database.objects.annotate('url', lowered_url=Lower('url')))
print(dict(database.objects.first('url')))

# def make_migrations(*tables):
#     """Writes the physical changes to the
#     local tables into the `migrations.json` file"""
#     import pathlib

#     from kryptone.conf import settings
#     settings['PROJECT_PATH'] = pathlib.Path(__file__).parent.parent.parent.joinpath('tests/testproject')
#     migrations = Migrations()
#     migrations.has_migrations = True
#     instances = {table.name: table}
#     migrations.migrate(instances)


# def migrate(*tables):
#     """Applies the migrations from the local
#     `migrations.json` file to the database"""
#     import pathlib

#     from kryptone.conf import settings
#     settings['PROJECT_PATH'] = pathlib.Path(__file__).parent.parent.parent.joinpath('tests/testproject')
#     migrations = Migrations()
#     instances = {table.name: table}
#     migrations.check(table_instances=instances)


# make_migrations()

# migrate()


# TODO: Implement cases
# 1. case when '1' then '2' else '3' end
# 2 case when '1' then '3' when '2' then '4'  else '5' end
# case {condition} end
# when {condition} then {then_value} else {else_value}

# TODO: Implement group by
# select rowid, *, count(rowid) from groupby rowid
# select rowid, *, count(rowid) from groupby rowid order by count(rowid) desc
# select rowid, *, count(rowid) from groupby rowid having count(rowid) > 1


# database = Database('seen_urls', table)
# database.make_migrations()
# database.migrate()

# table.create(url='http://google.com', visited=True)

# obj = namedtuple('Object', ['url'])
# table.bulk_create([obj('http://example.com')])
# import datetime
# table.create(url='http://example.com/1', visited=False, created_on=str(datetime.datetime.now()))

# r = table.get(rowid=4)

# r = table.filter(url__startswith='http')
# r = table.filter(url__contains='google')
# r = table.filter(rowid__in=[1, 4, 6])
# TODO: Use Field.to_database before evaluating the
# value to the dabase
# r = table.filter(rowid__in=[1, 4, 6], visited=False)
# r = table.filter(rowid__gte=3)
# r = table.filter(rowid__lte=3)
# r = table.filter(url__contains='/3')
# r = table.filter(url__startswith='http://')
# r = table.filter(url__endswith='/3')
# r = table.filter(rowid__range=[1, 3])
# r = table.filter(rowid__ne=1)
# r = table.filter(url__isnull=True)

# r['url'] = 'http://google.com/3'

# table.create(url='http://example.com')

# r = table.annotate(lowered_url=Lower('url'))
# r = table.annotate(uppered_url=Upper('url'))
# r = table.annotate(url_length=Length('url'))
# r = table.annotate(year=ExtractYear('created_on'))
# r = table.annotate(year=Max('rowid'))
# r = r.values()

# r = table.order_by('rowid')

# print(r)

# import time

# count = 1

# while True:
#     table.create(url=f'http://example.com/{count}')
#     count = count + 1
#     time.sleep(5)
#     print(table.all())
