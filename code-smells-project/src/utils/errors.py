"""Hierarquia de erros da aplicação, convertida em JSON pelo middleware de erros."""

# Algumas rotas originais devolvem {"erro": ..., "sucesso": False}; o campo extra preserva esse contrato.
SUCESSO_FALSO = {"sucesso": False}


class AppError(Exception):
    status_code = 500

    def __init__(self, message: str, *, extra: dict | None = None):
        super().__init__(message)
        self.message = message
        self.extra = dict(extra or {})


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
