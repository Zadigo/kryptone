import dataclasses
import json
import pathlib
import re
from dataclasses import field
from functools import cached_property
from urllib.parse import unquote, urlparse

from kryptone.utils.text import Text


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

    def set_collection_id(self, regex):
        return NotImplemented

    def as_csv(self):
        def convert_values(field):
            value = getattr(self, field)
            if isinstance(value, (list, tuple)):
                return ' / '.join(value)
            return value
        return list(map(convert_values, self.fields))


@dataclasses.dataclass
class Products(BaseModel):
    """A database to store products present on
    an e-commerce products page"""

    name: str
    price: str
    url: str
    image: str = None
    colors: list = field(default=list)
    other_information: str = None


@dataclasses.dataclass
class Product(BaseModel):
    """A simple database for storing pieces
    of information from an e-commerce 
    product page"""

    name: str
    description: str
    price: int
    url: str
    material: str = None
    discount_price: int = None
    breadcrumb: str = None
    collection_id: str = None
    number_of_colors: int = 1
    id_or_reference: str = None
    images: list = dataclasses.field(default_factory=list)
    composition: str = None
    color: str = None
    date: str = None
    sizes: list = dataclasses.field(default_factory=list)
    out_of_stock: bool = False
    inventory: str = None
    is_404: bool = False

    def __hash__(self):
        return hash((self.name, self.url, self.id_or_reference))

    @cached_property
    def get_images_url_objects(self):
        items = []
        for url in self.images:
            items.append(urlparse(url))
        return items

    @cached_property
    def number_of_images(self):
        return len(self.images)

    def set_collection_id(self, regex):
        """Set the product's collection ID from the url

        If the "collection_id" named parameter is present in the regex, 
        the result of the match will return this specific value otherwise
        it will be result of the first group

        >>> set_collection_id(r'\/(?P<collection_id>\d+)')
        """
        result = re.search(regex, self.get_url_object.path)
        if result:
            group_dict = result.groupdict()
            self.collection_id = group_dict.get(
                'collection_id',
                result.group(1)
            )

    def complex_name(self):
        name = str(Text(self.name, punctation=True, accents=True))
        name = name.replace(' ', '_')
        if self.id_or_reference is not None:
            return f'{name}_{self.id_or_reference}'
        return name
