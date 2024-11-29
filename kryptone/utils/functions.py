import random
import string
import pathlib

from kryptone.utils.text import (normalize_spaces, remove_accents,
                                 remove_punctuation)
from kryptone.utils.urls import URL


def directory_from_breadcrumbs(text, separator='>', remove_last=True, exclude=[]):
    """Get the path the local directory for the breadcrumb
    provided on the current page

    >>> text = "Bébé fille > T-shirt, polo, sous pull > T-shirt manches longues en coton bio à message printé"
    ... directory_from_breadcrumbs(text)
    ... "bébé_fille/tshirt_polo_sous_pull"
    """
    clean_text = normalize_spaces(text.lower())
    tokens = clean_text.split(separator)

    # Generally the last item of a breadcrumb
    # is the current page and first element
    # the home page
    if remove_last:
        tokens = tokens[0:len(tokens) - 1]

    clean_tokens = map(lambda x: x.strip(), tokens)

    if exclude:
        tokens = list(filter(lambda x: x not in exclude, clean_tokens))

    def build(token):
        token = remove_punctuation(token.strip()).replace(' ', '_')
        return token.lower()

    tokens = map(build, tokens)
    return pathlib.Path('/'.join(tokens))


def directory_from_url(url_or_path, exclude=[]):
    """Build the logical local directory in the local project
    using the natural structure of the product url

    >>> path = '/ma/woman/clothing/dresses/short-dresses/shirt-dress-1.html'
    ... directory_from_url(path, exclude=['ma'])
    ... "/woman/clothing/dresses/short-dresses"
    """
    if isinstance(url_or_path, URL):
        url_or_path = url_or_path.url_object.path

    tokens = url_or_path.split('/')
    tokens = filter(lambda x: x not in exclude and x != '', tokens)

    def clean_token(token):
        result = token.replace('-', '_')
        return remove_accents(remove_punctuation(result.lower(), keep=['_']))
    tokens = list(map(clean_token, tokens))

    tokens.pop(-1)
    return pathlib.Path('/'.join(tokens))


def create_filename(length=5, extension=None, suffix=None, suffix_with_date=False):
    characters = string.ascii_lowercase + string.digits
    name = ''.join(random.choice(characters) for _ in range(length))

    if suffix is not None:
        name = f'{name}_{suffix}'

    if suffix is None and suffix_with_date:
        from kryptone.utils.date_functions import get_current_date

        current_date = str(get_current_date().date()).replace('-', '_')
        name = f'{name}_{current_date}'

    if extension is not None:
        return f'{name}.{extension}'
    return name
