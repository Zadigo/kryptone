import pytz
import datetime
import calendar
from datetime import tzinfo


def get_current_date(timezone: str = pytz.UTC) -> datetime.datetime:
    """Returns the current date"""

    timezone = pytz.timezone(timezone)
    return datetime.datetime.now(timezone)


def is_expired(d: datetime.datetime, timezone: tzinfo = pytz.UTC) -> bool:
    """Checks if a date is expired by comparing it
    to the current date"""
    if not isinstance(d, datetime.datetime):
        raise ValueError("d should be a datetime object")
    date = get_current_date(timezone=timezone)
    return d > date


def get_weekday(d: datetime.datetime) -> int:
    if not isinstance(d, datetime.datetime):
        raise ValueError("d should be a datetime object")
    return calendar.weekday(d.year, d.month, d.day)


def get_month(d: datetime.datetime) -> int:
    if not isinstance(d, datetime.datetime):
        raise ValueError("d should be a datetime object")
    return calendar.month(d.year, d.month)


def get_monthrange(d: datetime.datetime) -> tuple[int, int]:
    if not isinstance(d, datetime.datetime):
        raise ValueError("d should be a datetime object")
    return calendar.monthrange(d.year, d.month)


def get_day_as_string(d: datetime.datetime) -> str:
    result = get_weekday(d)
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    return days[result]
