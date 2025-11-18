import pathlib
from subprocess import call
from unittest import TestCase
from unittest.mock import patch

from kryptone.base import get_selenium_browser_instance


class TestProject(TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def test_structure(self):
        with patch('kryptone.base.get_selenium_browser_instance') as mock_browser:
            mock_browser.return_value = mock_browser

            path = pathlib.Path('.').absolute()
            project = path.joinpath('tests/testproject')

            call([
                'python', 
                project.joinpath('manage.py'),
                'test_run', 
                'ExampleSpider'
            ])

            mock_browser.assert_called_once()
