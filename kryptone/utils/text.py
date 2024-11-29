import random
import re
import string
import unicodedata
from functools import cached_property

import unidecode

from kryptone.utils.iterators import drop_null

# ^(\d+[,.]?\d+)
PRICE = re.compile(r'(\d+\,?\d+)')

PRICE_EURO = re.compile(r'\d+\€\d+')


def parse_price(text):
    """From an incoming value, return
    it's float representation

    >>> parse_price('4,4 €')
    ... 4.4
    ... parse_price('4€4')
    ... 4.4
    """
    if isinstance(text, (int, float)):
        return text

    if text is None:
        return None

    format_one = PRICE_EURO.match(text)
    format_two = PRICE.search(text)

    if format_one:
        price = text.replace('€', '.')
    elif format_two:
        price = format_two.group(0)
    else:
        price = text
    price = price.replace(',', '.')
    return float(price)


def clean_text(text, encoding='utf-8'):
    if not isinstance(text, str):
        return text

    text = text.replace('\n', ' ')
    text = text.replace('\t', ' ')
    text = unicodedata.normalize('NFKD', text)
    text = text.encode(encoding).decode()
    return normalize_spaces(text)


class Text:
    """Represents a text string"""

    def __init__(self, text, punctation=False, accents=False):
        self.raw_text = text
        self.tokens = []
        self.punctation = punctation
        self.accents = accents
        self.encoding = 'utf-8'

    def __str__(self):
        cleaned_text = clean_text(self.raw_text, encoding=self.encoding)
        cleaned_text = cleaned_text.lower()

        if self.punctation:
            cleaned_text = remove_punctuation(cleaned_text)

        if self.accents:
            cleaned_text = remove_accents(cleaned_text)

        return cleaned_text

    def __add__(self, obj):
        return ' '.join([self.__str__(), str(obj)])

    def __len__(self):
        return len(self.__str__())

    def __iter__(self):
        for token in self.tokens:
            yield token

    @cached_property
    def tokens(self):
        return self.__str__().split(' ')


def remove_punctuation(text, keep=[], email_exception=False):
    """Remove the punctation from a given text. If the text
    is an email, consider using the email_exception so that the
    '@' symbol does not get removed"""
    punctuation = string.punctuation

    if keep:
        for value in keep:
            punctuation = punctuation.replace(value, '')

    if email_exception:
        punctuation = punctuation.replace('@', '')
    return text.translate(str.maketrans('', '', punctuation))


def remove_accents(text):
    """Remove accents from a given text"""
    return unidecode.unidecode(text)


def clean_dictionnary(item, accents=False, punctation=False):
    """Cleans each text values stored in a dictionnary

    >>> items = clean_dictionnary({'name': ' Kendall'})
    ... {'name': 'Kendall}
    """
    if item is None:
        return {}

    if isinstance(item, list):
        return [clean_dictionnary(data) for data in item]

    if not isinstance(item, dict):
        raise ValueError('Object to clean should a dictionnary')

    new_item = {}
    for key, value in item.items():
        if isinstance(value, str):
            if accents:
                value = remove_accents(accents)

            if punctation:
                value = remove_punctuation(value)
            new_item[key] = clean_text(value)
        else:
            new_item[key] = value
    return new_item


def normalize_spaces(text_or_tokens):
    """Remove excess spaces from a given text"""
    if isinstance(text_or_tokens, str):
        tokens = text_or_tokens.split(' ')
    else:
        tokens = text_or_tokens
    return ' '.join(drop_null(tokens))


def slugify(text):
    """Transforms a normal text into a slug

    >>> result = slugify('my text')
    ... 'my-text'
    """
    if not isinstance(text, str):
        raise ValueError(f'Value should be a text. Got: {type(text)}')
    text = text.replace(' ', '-').lower()
    return remove_accents(text)
