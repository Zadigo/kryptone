import dataclasses
import re
from functools import cached_property, lru_cache
from urllib.parse import urlparse


class BaseModel:
    @cached_property
    def fields(self):
        """Get the fields present on the model"""
        fields = dataclasses.fields(self)
        return list(map(lambda x: x.name, fields))
    
    @cached_property
    def url_object(self):
        return urlparse(getattr(self, 'url', ''))
    
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


@dataclasses.dataclass
class Product(BaseModel):
    """A simple database for storing pieces
    of information from an e-commerce product"""

    name: str
    description: str
    price: int
    url: str
    # collection_id: str = None
    # number_of_colors: int = 1
    # images:str = dataclasses.field(default_factory=[])
    # color: str = None
    
    def get_collection_id(self, regex):
        result = re.search(regex, getattr(self, 'url'))
        if result:
            return result.group(1)
        return None
