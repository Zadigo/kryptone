import re

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
