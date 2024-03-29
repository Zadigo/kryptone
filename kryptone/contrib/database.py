import datetime

from kryptone.db.fields import BooleanField, CharField, Field
from kryptone.db.tables import Database, Table

SEEN_URLS_TABLE = Table('seen_urls', fields=[
    CharField('url', unique=True),
    CharField('created_on', default=datetime.datetime.now)
])


URLS_TO_VISIT_TABLE = Table('url_to_visit', fields=[
    CharField('url', unique=True),
    BooleanField('visited', default=False),
    CharField('created_on', default=datetime.datetime.now)
])


VISITED_URLS_TABLE = Table('visited_urls', fields=[
    CharField('url', unique=True),
    CharField('created_on', default=datetime.datetime.now)
])


EXECUTION_TABLE = Table('execution_table', fields=[
    CharField('url'),
    CharField('created_on', default=datetime.datetime.now)
])


def get_database():
    """A wraper that returns the database instance
    because the __init__ of Database calls Migrations
    which calls settings.PROJECT_PATH which is None
    and raises an error when using Database in module"""
    return Database(
        'kryptone',
        SEEN_URLS_TABLE,
        URLS_TO_VISIT_TABLE,
        VISITED_URLS_TABLE,
        EXECUTION_TABLE
    )
