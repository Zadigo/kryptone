class BaseError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.message


class FileTypeError(BaseError):
    def __init__(self, message):
        super().__init__(message)


class ImproperlyConfiguredError(BaseError):
    """Error raised when a setting is not correctly configured
    """
    def __init__(self, message, **params):
        super().__init__(message)


class NoServerError(BaseError):
    """Error raised when a server is not implemented
    """
    def __init__(self, message, **params):
        super().__init__(message)


class NoPatternError(BaseError):
    """Error raised when a server is not implemented
    """
    def __init__(self, message, **params):
        super().__init__(message)
