class ProjectExistsError(Exception):
    def __init__(self):
        message = 'Project does not exist'
        super().__init__(message)
