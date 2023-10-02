import pytz
import datetime
import calendar


def get_current_date(timezone='utc'):
    """Returns the current date"""
    timezone = pytz.timezone(timezone)
    return datetime.datetime.now(tz=timezone)


def is_expired(d, timezone='utc'):
    """Checks if a date is expired by comparing it
    to the current date"""
    if not isinstance(d, datetime.datetime):
        raise ValueError('d should be a datetime object')
    date = get_current_date(timezone=timezone)
    return d > date


def get_weekday(d):
    if not isinstance(d, datetime.datetime):
        raise ValueError('d should be a datetime object')
    return calendar.weekday(d.year, d.month, d.day)


def get_month(d):
    if not isinstance(d, datetime.datetime):
        raise ValueError('d should be a datetime object')
    return calendar.month(d.year, d.month)


def get_monthrange(d):
    if not isinstance(d, datetime.datetime):
        raise ValueError('d should be a datetime object')
    return calendar.monthrange(d.year, d.month)


def get_day_as_string(d):
    result = get_weekday(d)
    days = [
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday'
    ]
    return days[result]
