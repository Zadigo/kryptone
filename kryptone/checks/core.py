from collections import OrderedDict

from kryptone.conf import settings
from kryptone.exceptions import ProjectExistsError


class GlobalMixins:
    _errors = []


class ApplicationChecks(GlobalMixins):
    """Base class for storing system checks"""

    def __init__(self):
        self._checks = OrderedDict()

    def run(self):
        """Base entrypoint for running project checks"""
        self.check_settings_base_integrity()

        for func in self._checks.values():
            new_errors = func()
            exceptions = [Exception(error) for error in new_errors]
            self._errors.extend(exceptions)

        if self._errors:
            # raise ImproperlyConfiguredError(self._errors)
            raise ExceptionGroup(
                "Project is improperly configured",
                self._errors
            )

    def check_settings_base_integrity(self):
        """
        Verifies that the integrity of the base variables 
        (PROJECT_PATH, PROXIES...) are correctly implemented 
        as they are intended to be
        """
        required_values = ['PROJECT_PATH', 'SPIDERS']
        keys = settings.keys()
        for value in required_values:
            if value not in keys:
                raise ValueError(
                    f"The following settings '{value}' are "
                    "required in your settings file."
                )

        requires_list_or_tuple = [
            'SPIDERS', 'ACTIVE_STORAGE_BACKENDS', 
            'WAIT_TIME_RANGE'
        ]
        for item in requires_list_or_tuple:
            value = getattr(settings, item)
            if not isinstance(value, (list, tuple)):
                raise ValueError(
                    f"{item} in settings.py should "
                    f"be a list or a tuple ex. {item} = []"
                )

        requires_dictionnary = ['STORAGE_BACKENDS']
        for item in requires_dictionnary:
            value = getattr(settings, item)
            if not isinstance(value, dict):
                raise ValueError(
                    f'{item} in settings.py should be a dictionnary'
                )

        # If Krytpone is called from a project configuration
        # we should automatically assume that it is a path
        PROJECT_PATH = getattr(settings, 'PROJECT_PATH', None)
        if PROJECT_PATH is None:
            raise ValueError((
                "PROJECT_PATH is empty. If you are using "
                "Krytpone outside of a project, call .configure(**kwargs)"
            ))

        # Also make sure that the path is one that really
        # exists in case the user changes this variable
        # to a 'string' path [...] thus breaking the
        # whole thing
        if not PROJECT_PATH.exists():
            raise ProjectExistsError()

        # Also make sure that this is
        # a directory
        if not PROJECT_PATH.is_dir():
            raise IsADirectoryError(
                "PROJECT_PATH should be the valid project's directory"
            )

    def register(self, tag=None):
        """Register a check on this class by using 
        this decorator on a custom function

        >>> @register
            def some_check():
                pass
        """
        TAG_NAME = tag
        def inner(func):
            if not callable(func):
                raise TypeError(
                    "A system check should be a callable "
                    "function to be registered"
                )
            # self._checks.append(func)
            tag = TAG_NAME or func.__name__
            self._checks[tag] = func
        return inner


checks_registry = ApplicationChecks()
