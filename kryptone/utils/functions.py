import pathlib
from kryptone.utils.text import normalize_spaces, remove_punctuation, remove_accents


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

    def build(token):
        token = remove_punctuation(token.strip()).replace(' ', '_')
        return token.lower()

    tokens = map(build, tokens)
    return pathlib.Path('/'.join(tokens))


def directory_from_url(path, exclude=[]):
    """Build the logical local directory in the local project
    using the natural structure of the product url

    >>> self.build_directory_from_url('/ma/woman/clothing/dresses/short-dresses/shirt-dress-1.html', exclude=['ma'])
    ... "/woman/clothing/dresses/short-dresses"
    """
    tokens = path.split('/')
    tokens = filter(lambda x: x not in exclude and x != '', tokens)

    def clean_token(token):
        result = token.replace('-', '_')
        return remove_accents(remove_punctuation(result.lower()))
    tokens = list(map(clean_token, tokens))

    tokens.pop(-1)
    return pathlib.Path('/'.join(tokens))
