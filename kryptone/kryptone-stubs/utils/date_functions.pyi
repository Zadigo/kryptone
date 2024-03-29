import datetime
from typing import Tuple

def get_current_date(timezone: str = ...) -> datetime.datetime: ...


def is_expired(d: datetime.datetime = ..., timezone: str = ...) -> bool: ...


def get_weekday(d: datetime.datetime = ...) -> int: ...


def get_month(d: datetime.datetime = ...) -> int: ...


def get_monthrange(d: datetime.datetime) -> Tuple[int, int]: ...


def get_day_as_string(d: datetime.datetime) -> str: ...
