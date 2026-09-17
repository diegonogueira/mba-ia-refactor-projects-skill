"""Validação dos payloads de usuário e de login."""
from src.models.user_model import DEFAULT_ROLE, MIN_PASSWORD_LENGTH, USER_ROLES
from src.utils.errors import ConflictError, ValidationError
from src.utils.validators import is_valid_email, require_json_object

NAME_REQUIRED_MESSAGE = 'Nome é obrigatório'
NAME_INVALID_MESSAGE = 'Nome inválido'
EMAIL_REQUIRED_MESSAGE = 'Email é obrigatório'
EMAIL_INVALID_MESSAGE = 'Email inválido'
EMAIL_TAKEN_MESSAGE = 'Email já cadastrado'
PASSWORD_REQUIRED_MESSAGE = 'Senha é obrigatória'
PASSWORD_INVALID_MESSAGE = 'Senha inválida'
PASSWORD_TOO_SHORT_ON_CREATE_MESSAGE = 'Senha deve ter no mínimo 4 caracteres'
PASSWORD_TOO_SHORT_ON_UPDATE_MESSAGE = 'Senha muito curta'
ROLE_INVALID_MESSAGE = 'Role inválido'
ACTIVE_INVALID_MESSAGE = 'Campo active inválido'
CREDENTIALS_REQUIRED_MESSAGE = 'Email e senha são obrigatórios'

ACTIVE_VALUES = (True, False, None)


def _password(value, too_short_message: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(PASSWORD_INVALID_MESSAGE)
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(too_short_message)
    return value


def _name(value) -> str:
    if not isinstance(value, str):
        raise ValidationError(NAME_INVALID_MESSAGE)
    return value


def _role(value) -> str:
    if value not in USER_ROLES:
        raise ValidationError(ROLE_INVALID_MESSAGE)
    return value


def _active(value):
    if value not in ACTIVE_VALUES:
        raise ValidationError(ACTIVE_INVALID_MESSAGE)
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
    if not is_valid_email(email):
        raise ValidationError(EMAIL_INVALID_MESSAGE)
    _password(password, PASSWORD_TOO_SHORT_ON_CREATE_MESSAGE)
    if email_in_use(email):
        raise ConflictError(EMAIL_TAKEN_MESSAGE)

    return {'name': _name(name), 'email': email, 'password': password, 'role': _role(role)}


def validate_user_changes(payload, *, email_in_use) -> dict:
    data = require_json_object(payload)
    changes = {}

    if 'name' in data:
        changes['name'] = _name(data['name'])
    if 'email' in data:
        email = data['email']
        if not is_valid_email(email):
            raise ValidationError(EMAIL_INVALID_MESSAGE)
        if email_in_use(email):
            raise ConflictError(EMAIL_TAKEN_MESSAGE)
        changes['email'] = email
    if 'password' in data:
        changes['password'] = _password(data['password'], PASSWORD_TOO_SHORT_ON_UPDATE_MESSAGE)
    if 'role' in data:
        changes['role'] = _role(data['role'])
    if 'active' in data:
        changes['active'] = _active(data['active'])
    return changes


def validate_credentials(payload) -> tuple[str, str]:
    data = require_json_object(payload)
    email = data.get('email')
    password = data.get('password')
    if not email or not password or not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError(CREDENTIALS_REQUIRED_MESSAGE)
    return email, password
