import dataclasses
import re
from dataclasses import field
from functools import cached_property
from urllib.parse import urlparse

from kryptone.db.models import BaseModel
from kryptone.utils.text import Text


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
    old_price: int = None
    breadcrumb: str = None
    collection_id: str = None
    number_of_colors: int = 1
    id_or_reference: str = None
    images: list = dataclasses.field(default_factory=list)
    composition: str = None
    color: str = None
    date: str = None
    sizes: list = dataclasses.field(default_factory=list)
    out_of_stock: bool = None

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


@dataclasses.dataclass
class GoogleBusiness(BaseModel):
    name: str = None
    url: str = None
    feed_url: str = None
    address: str = None
    rating: str = None
    latitude: int = None
    longitude: int = None
    number_of_reviews: int = None
    additional_information: list = field(default_factory=list)
    comments: str = field(default_factory=list)

    def as_csv(self):
        rows = []
        for comment in self.comments:
            row = [
                self.name, self.url, self.address, self.rating,
                self.number_of_reviews, comment['period'],
                comment['text']
            ]
            rows.append(row)
        header = [*self.fields, 'comment_period', 'comment_text']
        return rows.insert(0, header)

    def get_gps_coordinates_from_url(self, substitute_url=None):
        result = re.search(
            r'\@(\d+\.?\d+)\,?(\d+\.?\d+)',
            substitute_url or self.feed_url
        )
        if result:
            self.latitude = result.group(1)
            self.longitude = result.group(2)
            return result.groups()
        return False


@dataclasses.dataclass
class GoogleSearch:
    title: str
    url: str
