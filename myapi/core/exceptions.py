from ninja.responses import Response


class APIException(Exception):
    """Base exception class for API errors."""

    def __init__(self, message: str, name: str, status_code: int = 500):
        self.name = name
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ServiceError(APIException):
    """Raised when services fails."""

    def __init__(
        self,
        message: str = 'An unknown Service Error occurred.',
        name: str = 'ServiceError',
        status_code: int = 503
    ):
        super().__init__(message, name, status_code)


class ValidationError(APIException):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str = 'Validation error occurred.',
        name: str = 'ValidationError',
        status_code: int = 400
    ):
        super().__init__(message, name, status_code)


class NotFoundError(APIException):
    """Raised when resource is not found."""

    def __init__(
        self,
        message: str = 'Resource not found.',
        name: str = 'NotFoundError',
        status_code: int = 404
    ):
        super().__init__(message, name, status_code)


class ConflictError(APIException):
    """Raised when resource already exists."""

    def __init__(
        self,
        message: str = 'Resource already exists.',
        name: str = 'ConflictError',
        status_code: int = 409
    ):
        super().__init__(message, name, status_code)


class UnauthorizedError(APIException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = 'Invalid credentials.',
        name: str = 'UnauthorizedError',
        status_code: int = 401
    ):
        super().__init__(message, name, status_code)
