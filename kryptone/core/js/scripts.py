from functools import cached_property

from kryptone.conf import settings


class BaseScripts:
    def __init__(self, filename):
        self.path = settings.GLOBAL_KRYPTONE_PATH / f'core/js/scripts/{filename}'

    def __str__(self):
        return self.content

    @cached_property
    def content(self):
        with open(self.path, mode='r') as f:
            text = f.read()
            return text

class GoogleComments(BaseScripts):
    def __init__(self):
        super().__init__('maps/comments.js')


google_comments = GoogleComments()
