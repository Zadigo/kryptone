class BaseMessages:
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return f"{self.__class__.__name__}: message={self.message}"


class Info(BaseMessages):
    def __init__(self, message):
        super().__init__(message)

