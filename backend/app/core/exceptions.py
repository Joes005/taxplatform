from typing import Any


class AppException(Exception):
    """Base class for all application-level errors.

    Carries an HTTP status code and a machine-readable error code so the
    global exception handler can translate it into the platform's standard
    error envelope without route handlers needing to know about HTTP details.
    """

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None) -> None:
        self.message = message
        self.code = code or self.code
        self.details = details
        super().__init__(message)


class NotFoundError(AppException):
    status_code = 404
    code = "NOT_FOUND"


class ValidationAppError(AppException):
    status_code = 422
    code = "VALIDATION_ERROR"


class AuthenticationError(AppException):
    status_code = 401
    code = "AUTHENTICATION_FAILED"


class PermissionDeniedError(AppException):
    status_code = 403
    code = "PERMISSION_DENIED"


class DuplicateResourceError(AppException):
    status_code = 409
    code = "DUPLICATE_RESOURCE"


class ConflictError(AppException):
    status_code = 409
    code = "CONFLICT"


class InvalidStateError(AppException):
    status_code = 400
    code = "INVALID_STATE"
