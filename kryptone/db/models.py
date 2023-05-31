
import dataclasses

@dataclasses.dataclass
class Product:
    url: str
    name: str
    old_price: int = None
    new_price: int = None

    def get_items(self):
        return self.__dict__
