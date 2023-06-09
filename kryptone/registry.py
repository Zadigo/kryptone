import inspect
import os
from collections import OrderedDict
from functools import lru_cache
from importlib import import_module
from pathlib import Path

from kryptone import logger
from kryptone.conf import settings
from kryptone.signals import Signal
from kryptone.utils.urls import URLFile

# registry_populated = Signal()
# pre_init_spider = Signal()

SPIDERS_MODULE = 'spiders'

ENVIRONMENT_VARIABLE = 'KRYPTONE_SPIDER'


class SpiderConfig:
    """
    Class that represents a spider and 
    its overall different configurations
    """

    def __init__(self, name, spiders_module):
        self.name = name
        self.dotted_path = None
        self.registry = None
        self.initial_start_urls = []
        self.spider_class = getattr(spiders_module, name, None)
        self.is_automater = False

        self.MODULE = spiders_module

        paths = list(getattr(self.MODULE, '__path__', []))
        if not paths:
            filename = getattr(self.MODULE, '__file__', None)
            if filename is not None:
                paths = [os.path.dirname(filename)]

        # if len(paths) > 1:
        #     raise ValueError("There are multiple modules "
        #     "trying to start spiders")

        if not paths:
            raise ValueError("No spiders module within your project. "
                             "Please create a 'spiders.py' module.")

        self.path = paths[0]
        self.is_ready = False

    def __repr__(self):
        return f"<{self.__class__.__name__} for {self.name}>"

    @classmethod
    def create(cls, name, module):
        instance = cls(name, module)
        return instance

    def check_ready(self):
        """Marks the spider as configured and
        ready to be used"""
        if self.spider_class is not None and self.name is not None:
            self.is_ready = True

    def run(self, **kwargs):
        """Runs the spider by calling the spider class
        which in return calls "start" method on the
        spider via the __init__ method"""
        if self.spider_class is None:
            raise ValueError(
                f'Could not start spider in project: {self.dotted_path}'
            )
        spider_instance = self.spider_class()

        # TODO: Import the browser that we are
        # going to use with Selenium
        python_path = settings.WEBDRIVER['driver']
        module, klass = python_path.rsplit('.', maxsplit=1)
        selenium_module = import_module(module)
        browser = getattr(selenium_module, klass, None)

        try:
            spider_instance.start(**kwargs)
        except KeyboardInterrupt:
            spider_instance.create_dump()
        except Exception as e:
            spider_instance.create_dump()
            raise ExceptionGroup(
                'Multiple exceptions occurred',
                [
                    Exception(e)
                ]
            )


class MasterRegistry:
    def __init__(self):
        self.is_ready = False
        self.spiders_ready = False
        self.spiders = OrderedDict()
        self.project_name = None
        self.absolute_path = None
        self.middlewares = []
        self.has_running_spiders = False

    @property
    def has_spiders(self):
        return len(self.spiders.keys()) > 0

    @lru_cache(maxsize=1)
    def get_spiders(self):
        return self.spiders.values()

    def has_spider(self, name):
        return name in self.spiders

    def check_spiders_ready(self):
        if not self.has_spiders:
            raise ValueError(("Spiders are not yet loaded or "
                              "there are no registered ones."))

    def pre_configure_project(self, dotted_path, settings):
        # If the user did not explicitly set the path
        # to a MEDIA_FOLDER, we will be doing it
        # autmatically here
        media_folder = getattr(settings, 'MEDIA_FOLDER')
        if media_folder is None or media_folder == 'media':
            media_path = settings.PROJECT_PATH.joinpath('media')
        else:
            media_path = Path(settings.MEDIA_FOLDER)

        if not media_path.exists():
            raise ValueError("MEDIA_FOLDER path does does not exist")
        setattr(settings, 'MEDIA_FOLDER', media_path)

        self.is_ready = True

    def populate(self):
        dotted_path = os.environ.get(ENVIRONMENT_VARIABLE, None)

        if dotted_path is None:
            # The user is lauching the application outside
            # of a project (standalone), it's
            # his responsibility to provide a module where
            # the spiders are located. This is done in order
            # to not completly block the project from functionning
            raise ValueError('Requires project')

        try:
            project_module = import_module(dotted_path)
        except ImportError:
            raise ImportError(
                f"Could not load the project's related module: '{dotted_path}'"
            )

        from kryptone.app import BaseCrawler, SinglePageAutomater
        from kryptone.conf import settings

        self.absolute_path = Path(project_module.__path__[0])
        self.project_name = self.absolute_path.name
        setattr(settings, 'PROJECT_PATH', self.absolute_path)

        try:
            spiders_module = import_module(f'{dotted_path}.{SPIDERS_MODULE}')
        except Exception as e:
            raise ExceptionGroup(
                "Project loading fail",
                [
                    Exception(e.args),
                    ImportError(
                        "Failed to load the project's spiders submodule")
                ]
            )

        # Check that there are class objects that can be used
        # and are subclasses of the main Spider class object
        elements = inspect.getmembers(
            spiders_module,
            predicate=inspect.isclass
        )

        valid_spiders = filter(lambda x: issubclass(
            x[1], (BaseCrawler, SinglePageAutomater)), elements)
        valid_spider_names = list(map(lambda x: x[0], valid_spiders))

        # try:
        #     # Load the urls.py file which might contain
        #     # initial urls to use for the crawling
        #     urls_module = import_module(f'{dotted_path}.urls')
        # except ImportError:
        #     pass
        # else:
        #     initial_start_urls = []
        #     start_urls = getattr(urls_module, 'start_urls', [])
        #     for item in start_urls:
        #         if isinstance(item, URLFile):
        #             initial_start_urls.extend(list(item))

        #         if isinstance(item, str):
        #             initial_start_urls.append(item)

        for name in valid_spider_names:
            if name in settings.SPIDERS or name in settings.AUTOMATERS:
                instance = SpiderConfig.create(name, spiders_module)
                instance.registry = self
                # instance.initial_start_urls = initial_start_urls

                if name in settings.AUTOMATERS:
                    instance.is_automater = True

                self.spiders[name] = instance

        for config in self.spiders.values():
            config.check_ready()

        self.spiders_ready = True
        # registry_populated.send(self, registry=registry)

        # Cache the registry in the settings
        # file for performance reasons
        settings['REGISTRY'] = self

        self.pre_configure_project(dotted_path, settings)

    def run_all_automaters(self, **kwargs):
        if not self.has_spiders:
            logger.info(("There are no registered spiders in your project. If you created spiders, "
                         "register them within the SPIDERS variable of your "
                         "settings.py file."), Warning, stacklevel=0)
        else:
            for config in self.get_spiders():
                # pre_init_spider.send(self, spider=config)

                if not config.is_automater:
                    raise ValueError(f'{config} is not an automater')

                try:
                    config.run(**kwargs)
                except Exception:
                    logger.critical((f"Could not start {config}. "
                                     "Did you use the correct class name?"), stack_info=True)
                    raise

    def run_all_spiders(self, **kwargs):
        if not self.has_spiders:
            message = ("There are no registered spiders in your project. If you created spiders, "
                       "register them within the SPIDERS variable of your "
                       "settings.py file.")
            logger.info(message, Warning, stacklevel=0)
        else:
            for config in self.get_spiders():
                # pre_init_spider.send(self, spider=config)
                try:
                    self.has_running_spiders = True
                    config.run(**kwargs)
                except Exception as e:
                    message = f"Could not start {config}. Did you use the correct class name?"
                    raise ExceptionGroup(
                        message,
                        [
                            Exception(e)
                        ]
                    )

    def get_spider(self, spider_name):
        self.check_spiders_ready()
        try:
            return self.spiders[spider_name]
        except KeyError:
            message = (f"The spider with the name '{spider_name}' does not "
                       f"exist in the registry. Available spiders are {', '.join(self.spiders.keys())}. "
                       f"If you forgot to register '{spider_name}', check your settings file.")
            raise ExceptionGroup(
                message,
                [
                    ValueError(spider_name)
                ]
            )


registry = MasterRegistry()
