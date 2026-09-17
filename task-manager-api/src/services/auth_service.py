"""Credential verification and token issuing."""
from itsdangerous import URLSafeTimedSerializer

from src.models import User
from src.utils.errors import ForbiddenError, UnauthorizedError

TOKEN_SALT = "auth-token"


class AuthService:
    def __init__(self, secret_key: str):
        self._serializer = URLSafeTimedSerializer(secret_key, salt=TOKEN_SALT)

    def authenticate(self, email: str, password: str) -> User:
        user = User.find_by_email(email)
        if user is None or not user.verify_password(password):
            raise UnauthorizedError("Credenciais inválidas")
        if not user.active:
            raise ForbiddenError("Usuário inativo")
        return user

    def issue_token(self, user: User) -> str:
        return self._serializer.dumps({"user_id": user.id})
