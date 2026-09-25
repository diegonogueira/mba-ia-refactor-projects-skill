"""Hierarquia de erros da aplicação: cada camada levanta, o error handler central traduz em resposta."""


class AppError(Exception):
    """Erro esperado da aplicação, com o status HTTP correspondente."""

    status_code = 500
    headers: dict[str, str] = {}

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class AuthenticationRequiredError(UnauthorizedError):
    """Rota protegida chamada sem token válido: indica ao cliente o esquema esperado."""

    headers = {'WWW-Authenticate': 'Bearer'}


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class PersistenceError(AppError):
    """Falha ao gravar no banco; a mensagem é a que a API já devolvia nesses casos."""

    status_code = 500
