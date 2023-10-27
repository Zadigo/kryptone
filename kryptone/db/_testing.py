import datetime

from kryptone.db import tables
from kryptone.db.fields import BooleanField, Field
from kryptone.db.migrations import Migrations
from kryptone.db.functions import Lower, ExtractYear
from kryptone.db.tables import Table

table = Table('seen_urls', 'scraping', fields=[
        Field('url'),
        BooleanField('visited', default=False),
        Field('created_on')
    ],
    constraints=[
        
    ]
    # index=[
    #     Index('for_urls', 'url')
)
table.prepare()





def make_migrations(*tables):
    """Writes the physical changes to the
    local tables into the `migrations.json` file"""
    import pathlib

    from kryptone.conf import settings
    settings['PROJECT_PATH'] = pathlib.Path(__file__).parent.parent.parent.joinpath('tests/testproject')
    migrations = Migrations()
    migrations.has_migrations = True
    instances = {table.name: table}
    migrations.migrate(instances)


def migrate(*tables):
    """Applies the migrations from the local
    `migrations.json` file to the database"""
    import pathlib

    from kryptone.conf import settings
    settings['PROJECT_PATH'] = pathlib.Path(__file__).parent.parent.parent.joinpath('tests/testproject')
    migrations = Migrations()
    instances = {table.name: table}
    migrations.check(table_instances=instances)


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
r = table.annotate(year=ExtractYear('created_on'))
# r = r.values()

# r = table.order_by('rowid')

print(r)

# import time

# count = 1

# while True:
#     table.create(url=f'http://example.com/{count}')
#     count = count + 1
#     time.sleep(5)
#     print(table.all())
