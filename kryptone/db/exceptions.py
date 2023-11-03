class ImproperlyConfiguredError(Exception):
    def __init__(self, table, message):
        super().__init__(message)
