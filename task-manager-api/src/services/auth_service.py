"""Autenticação: verifica credenciais, emite tokens assinados e identifica quem chama pelo token."""
from itsdangerous import BadSignature, URLSafeTimedSerializer

from src.models.user_model import User
from src.utils.errors import AuthenticationRequiredError, ForbiddenError, UnauthorizedError
from src.utils.validators import is_integer

TOKEN_SALT = 'auth-token'
INVALID_CREDENTIALS_MESSAGE = 'Credenciais inválidas'
INACTIVE_USER_MESSAGE = 'Usuário inativo'
AUTHENTICATION_REQUIRED_MESSAGE = 'Autenticação necessária'
INVALID_TOKEN_MESSAGE = 'Token inválido ou expirado'


class AuthService:
    def __init__(self, secret_key: str, token_max_age: int):
        self._serializer = URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT)
        self._token_max_age = token_max_age

    def authenticate(self, email: str, password: str) -> User:
        """Valida e-mail e senha de um usuário ativo."""
        user = User.get_by_email(email)
        if user is None or not user.check_password(password):
            raise UnauthorizedError(INVALID_CREDENTIALS_MESSAGE)
        if not user.active:
            raise ForbiddenError(INACTIVE_USER_MESSAGE)
        return user

    def issue_token(self, user: User) -> str:
        """O token carrega só o id; o papel é lido do banco a cada requisição."""
        return self._serializer.dumps({'user_id': user.id})

    def user_from_token(self, token: str) -> User:
        """Usuário ativo dono de um token íntegro e dentro da validade (401 caso contrário)."""
        if not token:
            raise AuthenticationRequiredError(AUTHENTICATION_REQUIRED_MESSAGE)
        try:
            payload = self._serializer.loads(token, max_age=self._token_max_age)
        except BadSignature:  # inclui SignatureExpired
            raise AuthenticationRequiredError(INVALID_TOKEN_MESSAGE) from None
        user_id = payload.get('user_id') if isinstance(payload, dict) else None
        user = User.get_by_id(user_id) if is_integer(user_id) else None
        if user is None:
            raise AuthenticationRequiredError(INVALID_TOKEN_MESSAGE)
        if not user.active:
            raise ForbiddenError(INACTIVE_USER_MESSAGE)
        return user
