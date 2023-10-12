import dataclasses
import pathlib
from functools import cached_property
from urllib.parse import unquote, urlparse

import pandas


class BaseModel:
    """Base class for all models"""

    def __getitem__(self, key):
        return getattr(self, key)

    @cached_property
    def fields(self):
        """Get the fields present on the model"""
        fields = dataclasses.fields(self)
        return list(map(lambda x: x.name, fields))

    @cached_property
    def get_url_object(self):
        result = unquote(getattr(self, 'url', ''))
        return urlparse(str(result))

    @cached_property
    def url_stem(self):
        return pathlib.Path(str(self.url)).stem

    def as_json(self):
        """Return the object as dictionnary"""
        item = {}
        for field in self.fields:
            item[field] = getattr(self, field)
        return item

    def as_csv(self):
        def convert_values(field):
            value = getattr(self, field)
            if isinstance(value, (list, tuple)):
                return ' / '.join(value)
            return value
        return list(map(convert_values, self.fields))
