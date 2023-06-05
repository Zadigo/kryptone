
import dataclasses
from dataclasses import field


@dataclasses.dataclass
class Product:
    url: str
    name: str
    images: str = field(default=[])
    pk: int = field(default=None)
    old_price: int = None
    new_price: int = None
    description: str = None

    def get_items(self):
        return self.__dict__

    def add_image(self, value):
        pass
