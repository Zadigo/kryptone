import re
import string
import secrets
import unidecode

from kryptone.utils.iterators import drop_null

# ^(\d+[,.]?\d+)
PRICE = re.compile(r'(\d+\,?\d+)')

PRICE_EURO = re.compile(r'\d+\€\d+')


def random_string(n=10):
    return secrets.token_hex(nbytes=n)


def create_filename(extension='json'):
    """Generates a new filename with an extension"""
    return f'{random_string()}.{extension}'


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


def clean_text(text):
    if not isinstance(text, str):
        return text
    items = text.split('\n')
    text = ' '.join(items)

    items = drop_null(text.split(' '))
    return ' '.join(items)


class Text:
    """Represents a text string"""

    def __init__(self, text):
        text = self.simple_clean(text)
        self.tokens = list(drop_null(text.split(' ')))
        self.text = ' '.join(self.tokens)

    def __str__(self):
        return self.text

    def __add__(self, obj):
        return ' '.join([self.text, str(obj)])

    def __len__(self):
        return len(self.text)

    def __iter__(self):
        for token in self.tokens:
            yield token

    @staticmethod
    def simple_clean(text, encoding='utf-8'):
        """Applies simple cleaning techniques on the
        text by removing newlines, lowering the characters
        and removing extra spaces"""
        result2 = re.sub('\W', ' ', text)
        lowered_text = str(text).lower().strip()
        text = lowered_text.encode(encoding).decode(encoding)
        normalized_text = text.replace('\n', ' ')
        return normalized_text.strip()


def remove_punctuation(text, email_exception=False):
    """Remove the punctation from a given text. If the text
    is an email, consider using the email_exception so that the
    '@' symbol does not get removed"""
    punctuation = string.punctuation
    if email_exception:
        punctuation = punctuation.replace('@', '')
    return text.translate(str.maketrans('', '', punctuation))


def remove_accents(text):
    """Remove accents from the text"""
    return unidecode.unidecode(text)
