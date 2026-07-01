from abc import ABC, abstractmethod
from typing import Optional
from typing import Optional

from selenium.webdriver import Chrome, ChromeOptions, Edge, EdgeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.proxy import Proxy, ProxyType
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

from kryptone.conf import settings
from kryptone.utils.randomizers import RANDOM_USER_AGENT


class SeleniumBrowser(ABC):
    """A base interface class for launching Selenium
    browsers with customizable options.

    Args:
        browser_name (Optional[str]): The name of the browser to launch.
        headless (bool): Whether to launch the browser in headless mode.
        load_images (bool): Whether to load images in the browser.
        load_js (bool): Whether to load JavaScript in the browser.

    Raises:
        ConnectionError: If there is an error while installing the browser driver.
    """

    def __init__(
        self,
        browser_name: Optional[str] = None,
        headless: bool = False,
        load_images: bool = True,
        load_js: bool = True,
    ):
        self.browser_name = browser_name
        self.headless = headless
        self.load_images = load_images
        self.load_js = load_js

    @abstractmethod
    def initialize(self):
        browser_name = self.browser_name or settings.WEBDRIVER

        browser = Chrome if browser_name == "Chrome" else Edge
        manager_instance = (
            ChromeDriverManager
            if browser_name == "Chrome"
            else EdgeChromiumDriverManager
        )

        options_klass = ChromeOptions if browser_name == "Chrome" else EdgeOptions
        options = options_klass()
        options.add_argument("--remote-allow-origins=*")
        options.add_argument(f"--user-agent={RANDOM_USER_AGENT()}")
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        # Allow Selenium to be launched
        # in headless mode
        if self.headless:
            options.headless = True

        # 0 = Default, 1 = Allow, 2 = Block
        preferences = {
            "profile.default_content_setting_values": {
                "images": 0 if self.load_images else 2,
                "javascript": 0 if self.load_js else 2,
                "popups": 2,
                "geolocation": 2,
                "notifications": 2,
            }
        }
        options.add_experimental_option("prefs", preferences)

        # Proxies
        if settings.PROXY_IP_ADDRESS is not None:
            proxy = Proxy()
            proxy.proxy_type = ProxyType.MANUAL
            proxy.http_proxy = settings.PROXY_IP_ADDRESS
            options.add_argument(f"--proxy-server=http://{settings.PROXY_IP_ADDRESS}")
            options.add_argument("--disable-gpu")

        try:
            service = Service(manager_instance().install())
        except Exception:
            raise ConnectionError("An error occurred. Are you offline?")
        return browser(service=service, options=options)


class SeleniumLauncher:
    """A class for launching Selenium browsers using a specified SeleniumBrowser instance.

    Args:
        instance (SeleniumBrowser): An instance of a SeleniumBrowser subclass.
    """

    def __init__(self, instance: SeleniumBrowser):
        self.instance = instance

    def launch(self):
        return self.instance.initialize()
