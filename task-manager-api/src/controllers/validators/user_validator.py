"""Validação dos payloads de usuário e de login."""
from src.models.user_model import (DEFAULT_ROLE, MAX_EMAIL_LENGTH, MAX_NAME_LENGTH, MIN_PASSWORD_LENGTH,
                                   SELF_SIGNUP_ROLES, USER_ROLES)
from src.utils.errors import ConflictError, ForbiddenError, ValidationError
from src.utils.validators import is_valid_email, require_json_object, validate_required_text

NAME_REQUIRED_MESSAGE = 'Nome é obrigatório'
NAME_INVALID_MESSAGE = 'Nome inválido'
NAME_TOO_LONG_MESSAGE = 'Nome muito longo'
EMAIL_REQUIRED_MESSAGE = 'Email é obrigatório'
EMAIL_INVALID_MESSAGE = 'Email inválido'
EMAIL_TOO_LONG_MESSAGE = 'Email muito longo'
EMAIL_TAKEN_MESSAGE = 'Email já cadastrado'
PASSWORD_REQUIRED_MESSAGE = 'Senha é obrigatória'
PASSWORD_INVALID_MESSAGE = 'Senha inválida'
PASSWORD_TOO_SHORT_ON_CREATE_MESSAGE = f'Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres'
PASSWORD_TOO_SHORT_ON_UPDATE_MESSAGE = 'Senha muito curta'
ROLE_INVALID_MESSAGE = 'Role inválido'
CREDENTIALS_REQUIRED_MESSAGE = 'Email e senha são obrigatórios'

# O cadastro é público: quem se cadastra não escolhe privilégios.
ROLE_FORBIDDEN_MESSAGE = 'Não é possível definir esse role sem autenticação'
# A atualização é do próprio usuário (ou de um admin agindo como ele): privilégios não mudam por ela.
ROLE_CHANGE_FORBIDDEN_MESSAGE = 'Não é possível alterar o role por esta rota'
ACTIVE_CHANGE_FORBIDDEN_MESSAGE = 'Não é possível alterar o campo active por esta rota'


def _password(value, too_short_message: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(PASSWORD_INVALID_MESSAGE)
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(too_short_message)
    return value


def _name(value) -> str:
    return validate_required_text(value, MAX_NAME_LENGTH, required_message=NAME_REQUIRED_MESSAGE,
                                  invalid_message=NAME_INVALID_MESSAGE, too_long_message=NAME_TOO_LONG_MESSAGE)


def _email(value) -> str:
    if not is_valid_email(value):
        raise ValidationError(EMAIL_INVALID_MESSAGE)
    if len(value) > MAX_EMAIL_LENGTH:
        raise ValidationError(EMAIL_TOO_LONG_MESSAGE)
    return value


def _self_signup_role(value) -> str:
    """Cadastro público só cria o papel menos privilegiado; pedir outro é recusado."""
    if value not in USER_ROLES:
        raise ValidationError(ROLE_INVALID_MESSAGE)
    if value not in SELF_SIGNUP_ROLES:
        raise ForbiddenError(ROLE_FORBIDDEN_MESSAGE)
    return value


def validate_new_user(payload, *, email_in_use) -> dict:
    data = require_json_object(payload)

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', DEFAULT_ROLE)

    if not name:
        raise ValidationError(NAME_REQUIRED_MESSAGE)
    if not email:
        raise ValidationError(EMAIL_REQUIRED_MESSAGE)
    if not password:
        raise ValidationError(PASSWORD_REQUIRED_MESSAGE)
    email = _email(email)
    _password(password, PASSWORD_TOO_SHORT_ON_CREATE_MESSAGE)
    if email_in_use(email):
        raise ConflictError(EMAIL_TAKEN_MESSAGE)

    return {'name': _name(name), 'email': email, 'password': password, 'role': _self_signup_role(role)}


def validate_user_changes(payload, *, email_in_use) -> dict:
    data = require_json_object(payload)

    # Esta rota edita o perfil; papel e ativação são gestão de privilégios e não passam por ela.
    if 'role' in data:
        raise ForbiddenError(ROLE_CHANGE_FORBIDDEN_MESSAGE)
    if 'active' in data:
        raise ForbiddenError(ACTIVE_CHANGE_FORBIDDEN_MESSAGE)

    changes = {}
    if 'name' in data:
        changes['name'] = _name(data['name'])
    if 'email' in data:
        email = _email(data['email'])
        if email_in_use(email):
            raise ConflictError(EMAIL_TAKEN_MESSAGE)
        changes['email'] = email
    if 'password' in data:
        changes['password'] = _password(data['password'], PASSWORD_TOO_SHORT_ON_UPDATE_MESSAGE)
    return changes


def validate_credentials(payload) -> tuple[str, str]:
    data = require_json_object(payload)
    email = data.get('email')
    password = data.get('password')
    if not email or not password or not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError(CREDENTIALS_REQUIRED_MESSAGE)
    return email, password
