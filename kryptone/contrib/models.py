import dataclasses
import pathlib
import re
from dataclasses import field
from functools import cached_property, lru_cache
from urllib.parse import unquote, urlparse

from kryptone.utils.text import remove_accents, remove_punctuation


class BaseModel:
    """Base class for all models"""
    @cached_property
    def fields(self):
        """Get the fields present on the model"""
        fields = dataclasses.fields(self)
        return list(map(lambda x: x.name, fields))

    @cached_property
    def url_object(self):
        result = unquote(getattr(self, 'url', ''))
        return urlparse(str(result))

    @cached_property
    def get_url_object(self):
        return urlparse(str(self.url))

    @cached_property
    def url_stem(self):
        return pathlib.Path(str(self.url)).stem

    def __getitem__(self, key):
        return getattr(self, key)

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
    collection_id: str = None
    number_of_colors: int = 1
    id_or_reference: str = None
    id: int = None
    images: str = dataclasses.field(default_factory=[])
    composition: str = None
    color: str = None

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

    def build_directory_from_url(self, exclude=[]):
        """Build the logical local directory in the local project
        using the natural structure of the product url

        >>> self.build_directory_from_url('/ma/woman/clothing/dresses/short-dresses/shirt-dress-1.html', exclude=['ma'])
        ... "/woman/clothing/dresses/short-dresses"
        """
        tokens = self.url_object.path.split('/')
        tokens = filter(lambda x: x not in exclude and x != '', tokens)

        def clean_token(token):
            result = token.replace('-', '_')
            return remove_accents(remove_punctuation(result))
        tokens = list(map(clean_token, tokens))

        tokens.pop(-1)
        return pathlib.Path('/'.join(tokens))

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
                'collection_id', result.group(1))


@dataclasses.dataclass
class GoogleBusiness(BaseModel):
    name: str
    url: str
    address: str
    rating: str
    number_of_reviews: int
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
