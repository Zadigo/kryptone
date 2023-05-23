import os
from importlib import import_module


def import_from_module(dotted_path: str):
    """
    Imports a module, gets an object then
    tries to return it
    """
    try:
        path, klass = dotted_path.rsplit('.', maxsplit=1)
    except:
        raise ImportError(f"Module at path {path} does not exist.")

    module = import_module(path)

    try:
        return getattr(module, klass)
    except AttributeError:
        raise ImportError(f"Could not find attribute '{klass}' "
                          f"in module {dotted_path}.")


def module_directory(module):
    """Return the main directory of a module"""
    paths = list(getattr(module, '__path__', []))
    if len(paths) == 1:
        return paths[0]
    else:
        filename = getattr(module, '__file__', None)
        if filename is not None:
            return os.path.dirname(filename)
    raise ValueError("Could not determine module's directory.")


# m = import_module('selenium.webdriver')
# e = getattr(m, 'Edge')
# print(e(executable_path=os.environ.get('KRYPTONE_WEBDRIVER', None)))
