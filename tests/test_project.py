import pathlib
from subprocess import call
from unittest import TestCase
from unittest.mock import MagicMixin, MagicMock, Mock, patch
from kryptone.registry import registry


@patch('kryptone.base.Service')
@patch('kryptone.base.Chrome')
@patch('kryptone.base.ChromeDriverManager')
class TestProject(TestCase):
    def test_structure(self, mock_driver_manager, mock_chrome, mock_service):
        pass
        # path = pathlib.Path('.').absolute()
        # project = path.joinpath('tests/testproject')

        # call([
        #     'python3',
        #     project.joinpath('manage.py'),
        #     'test_run',
        #     'ExampleSpider'
        # ])

        # mock_browser.assert_called_once()

        # with patch('kryptone.base.get_selenium_browser_instance') as mock_browser:
        # with patch('selenium.webdriver.Chrome') as mock_browser:
        # mock_browser.return_value = mock_browser

        # path = pathlib.Path('.').absolute()
        # project = path.joinpath('tests/testproject')

        # call([
        #     'python3',
        #     project.joinpath('manage.py'),
        #     'test_run',
        #     'ExampleSpider'
        # ])

        # mock_browser.assert_called_once()
