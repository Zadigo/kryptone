class ProjectExistsError(Exception):
    def __init__(self):
        message = 'Project does not exist'
        super().__init__(message)


class SpiderExecutionError(Exception):
    def __init__(self):
        message = 'Spider failed to complete'
        super().__init__(message)
