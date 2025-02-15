import dataclasses
import datetime
import decimal
import uuid
from json.encoder import JSONEncoder


class DefaultJsonEncoder(JSONEncoder):
    """An encoder specially created to encode datetime
    objects or other specific Python representations
    such as dataclasses"""

    def default(self, obj):
        from kryptone.utils.urls import URL

        # Date/Time string spcifications at ECMA 262
        # https://ecma-international.org/ecma-262/5.1/#sec-15.9.1.15

        if isinstance(obj, datetime.datetime):
            representation = obj.isoformat()
            if representation.endswith('+00:00'):
                representation = representation[:-6] + 'Z'
            return representation

        if isinstance(obj, datetime.time):
            if datetime.timezone and datetime.timezone.is_aware(obj):
                raise ValueError('Cannot represent timezone-aware times.')
            return obj.isoformat()

        if isinstance(obj, datetime.date):
            return str(obj)

        if isinstance(obj, datetime.timedelta):
            return str(obj.total_seconds())

        if isinstance(obj, decimal.Decimal):
            return float(obj)

        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)

        if isinstance(obj, URL):
            return str(obj)

        if isinstance(obj, uuid.UUID):
            return str(obj)

        if isinstance(obj, bytes):
            return obj.decode()

        if hasattr(obj, 'tolist'):
            return obj.tolist()

        # Conversion for lists and tuples
        if hasattr(obj, '__getitem__'):
            convert_to = list if isinstance(obj, (list, tuple)) else dict
            try:
                return convert_to(obj)
            except Exception:
                raise

        if hasattr(obj, '__iter__'):
            return tuple(item for item in obj)

        return super().default(obj)
