import dataclasses
import unittest

from kryptone.contrib.models import BaseModel


@dataclasses.dataclass
class MyModel(BaseModel):
    name: str


class TestBaseModel(unittest.TestCase):
    def setUp(self):
        self.instance = MyModel('Kendall Jenner')

    def test_structure(self):
        self.assertEqual(self.instance.name, 'Kendall Jenner')
        self.assertIsInstance(self.instance.as_json(), dict)
        self.assertIsInstance(self.instance.as_csv(), list)


if __name__ == '__main__':
    unittest.main()
