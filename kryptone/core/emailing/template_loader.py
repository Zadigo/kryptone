import os
from functools import cached_property

from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader
from zemailer.settings import configuration

environment = Environment()
loader = FileSystemLoader(
    os.path.join(
        configuration.PROJECT_PATH,
        'templates')
)


def get_template(name: str):
    return loader.load(environment, name)


def render_template(name: str, context: dict = {}):
    template = get_template(name)
    context = template.new_context(context)
    return template.render(**context)
