"""Autenticação: verifica credenciais e emite tokens assinados."""
import logging

from itsdangerous import URLSafeTimedSerializer

from src.models.user_model import User
from src.utils.errors import ForbiddenError, UnauthorizedError

logger = logging.getLogger(__name__)

TOKEN_SALT = 'auth-token'
INVALID_CREDENTIALS_MESSAGE = 'Credenciais inválidas'
INACTIVE_USER_MESSAGE = 'Usuário inativo'


class AuthService:
    def __init__(self, secret_key: str):
        self._serializer = URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT)

    def authenticate(self, email: str, password: str) -> User:
        """Valida e-mail e senha; migra hashes MD5 antigos no primeiro login bem-sucedido."""
        user = User.get_by_email(email)
        if user is None or not user.check_password(password):
            raise UnauthorizedError(INVALID_CREDENTIALS_MESSAGE)
        if user.has_legacy_hash():
            logger.info('Atualizando hash de senha legado: usuário id=%s', user.id)
            user.set_password(password)
            user.update()
        if not user.active:
            raise ForbiddenError(INACTIVE_USER_MESSAGE)
        return user

    def issue_token(self, user: User) -> str:
        return self._serializer.dumps({'user_id': user.id})
