import os
from functools import cached_property

from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader
from kryptone.conf import settings

environment = Environment()
loader = FileSystemLoader(
    os.path.join(
        settings.GLOBAL_KRYPTONE_PATH,
        'core/emailing/templates')
)


def get_template(name):
    return loader.load(environment, name)


def render_template(name, context={}):
    template = get_template(name)
    context = template.new_context(context)
    return template.render(**context)
