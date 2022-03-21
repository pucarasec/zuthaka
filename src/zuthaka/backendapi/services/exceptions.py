class ___Error(RuntimeError):
    pass


class InconsistencyError(RuntimeError):
    pass


class ResourceExistsError(InconsistencyError):
    pass


class ResourceNotFoundError(InconsistencyError):
    pass
