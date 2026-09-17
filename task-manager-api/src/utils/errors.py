"""Application error hierarchy, translated to HTTP responses by middlewares.error_handler."""


class AppError(Exception):
    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class PersistenceError(AppError):
    status_code = 500
