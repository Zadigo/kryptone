import inspect

from kryptone.utils.module_loaders import import_module


class Settings:
    """Global settings for a
    a Kryptone project"""

    MODULE = None

    def __init__(self):
        settings_file = import_module('kryptone.conf.base')
        for key, value in settings_file.__dict__.items():
            if key.startswith('__'):
                continue

            if key.isupper():
                setattr(self, key, value)
        self.MODULE = settings_file

    def __repr__(self):
        return f'<Settings>'

    def __getitem__(self, name):
        return getattr(self, name)

    def __setitem__(self, name, value):
        return setattr(self, name, value)

    def get(self, name):
        return self.__getitem__(name)


settings = Settings()
