import importlib
import os

from kryptone.constants import ENVIRONMENT_VARIABLE
from kryptone.utils.module_loaders import import_module


class UserSettings:
    SETTINGS_MODULE = None

    def __init__(self, dotted_path):
        self.configured = False
        if dotted_path is None:
            # If this class is called outside of a project,
            # the dotted path will be None. Just ignore
            # and consider that there is not project
            # settings.py file to be used
            pass
        else:
            module = importlib.import_module(f'{dotted_path}.settings')
            for key in dir(module):
                if key.isupper():
                    setattr(self, key, getattr(module, key))
            self.configured = True

            self.SETTINGS_MODULE = module

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value


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

        # This is the section that implements the settings that
        # the user modified or implemented to the global settings
        dotted_path = os.environ.get(ENVIRONMENT_VARIABLE)
        self._user_settings = UserSettings(dotted_path)

        list_or_tuple_settings = ['STORAGE_MEMCACHE_LOAD_BALANCER']
        for key in self._user_settings.__dict__.keys():
            if key.isupper():
                if key not in list_or_tuple_settings:
                    setattr(self, key, getattr(self._user_settings, key))
                else:
                    # In order to ensure that both the user setting
                    # and the global setting are used simultanuously,
                    # when dealing with tuples, lists [...] we have
                    # to collide/extend these elements
                    user_setting = getattr(self._user_settings, key)
                    global_setting = getattr(self, key)

                    if isinstance(user_setting, tuple):
                        user_setting = list(user_setting)
                    
                    if isinstance(user_setting, list):
                        user_setting.extend(global_setting)
                    elif isinstance(user_setting, dict):
                        user_setting = user_setting | global_setting

                    setattr(self, key, user_setting)

    def __repr__(self):
        if self._user_settings.configured:
            return f"<{self.__class__.__name__} [{self._user_settings.__repr__()}]>"
        return f"<{self.__class__.__name__}>"

    def __getitem__(self, name):
        return getattr(self, name)

    def __setitem__(self, name, value):
        return setattr(self, name, value)

    def get(self, name):
        return self.__getitem__(name)

    def keys(self):
        return [key for key in self.__dict__.keys()]


settings = Settings()
