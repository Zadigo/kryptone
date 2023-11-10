class ProjectExistsError(Exception):
    def __init__(self):
        message = 'Project does not exist'
        super().__init__(message)


class SpiderExecutionError(Exception):
    def __init__(self):
        message = 'An error occured during the execution of the crawl'
        super().__init__(message)


class SpiderExistsError(Exception):
    def __init__(self, name, spiders):
        names = ', '.join(spiders.keys())
        message = (
            f"The spider with the name '{name}' does not "
            f"exist in the registry. Available spiders are '{names}'."
        )
        super().__init__(message)


class BadImplementationError(Exception):
    def __init__(self, message):
        super().__init__(message)
