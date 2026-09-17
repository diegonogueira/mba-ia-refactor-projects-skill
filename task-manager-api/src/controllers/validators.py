"""Request payload validation. Messages and status codes follow the original API contract."""
import re
from collections.abc import Callable, Mapping
from datetime import datetime

from src.models.category_model import DEFAULT_COLOR
from src.models.task_model import (
    DEFAULT_PRIORITY,
    DEFAULT_STATUS,
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    VALID_STATUSES,
    Task,
)
from src.models.user_model import DEFAULT_ROLE, MIN_PASSWORD_LENGTH, VALID_ROLES
from src.utils.errors import ConflictError, NotFoundError, ValidationError

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$")
COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

ExistsCheck = Callable[[int], bool]


def require_json_object(payload, allow_empty: bool = False) -> dict:
    if not isinstance(payload, dict) or (not payload and not allow_empty):
        raise ValidationError("Dados inválidos")
    return payload


# --- tasks

def validate_new_task(payload: dict, user_exists: ExistsCheck, category_exists: ExistsCheck) -> dict:
    if not payload.get("title"):
        raise ValidationError("Título é obrigatório")
    return {
        "title": _title(payload["title"]),
        "description": _optional_text(payload.get("description", ""), "Descrição inválida"),
        "status": _status(payload.get("status", DEFAULT_STATUS)),
        "priority": _priority(payload.get("priority", DEFAULT_PRIORITY)),
        "user_id": _reference(payload.get("user_id"), user_exists, "Usuário não encontrado"),
        "category_id": _reference(payload.get("category_id"), category_exists, "Categoria não encontrada"),
        "due_date": _due_date(payload.get("due_date"), "Formato de data inválido. Use YYYY-MM-DD"),
        "tags": _tags(payload.get("tags") or None),
    }


def validate_task_changes(payload: dict, user_exists: ExistsCheck, category_exists: ExistsCheck) -> dict:
    validators = {
        "title": _title,
        "description": lambda value: _optional_text(value, "Descrição inválida"),
        "status": _status,
        "priority": _priority,
        "user_id": lambda value: _reference(value, user_exists, "Usuário não encontrado"),
        "category_id": lambda value: _reference(value, category_exists, "Categoria não encontrada"),
        "due_date": lambda value: _due_date(value, "Formato de data inválido"),
        "tags": _tags,
    }
    return {field: validate(payload[field]) for field, validate in validators.items() if field in payload}


def validate_search_filters(args: Mapping[str, str]) -> dict:
    return {
        "text": args.get("q", ""),
        "status": args.get("status", ""),
        "priority": _query_int(args.get("priority", ""), "Filtro priority inválido"),
        "user_id": _query_int(args.get("user_id", ""), "Filtro user_id inválido"),
    }


# --- users

def validate_new_user(payload: dict, email_taken: Callable[[str], bool]) -> dict:
    name, email, password = payload.get("name"), payload.get("email"), payload.get("password")
    if not name:
        raise ValidationError("Nome é obrigatório")
    if not email:
        raise ValidationError("Email é obrigatório")
    if not password:
        raise ValidationError("Senha é obrigatória")
    fields = {
        "name": _name(name),
        "email": _email(email),
        "password": _password(password, f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres"),
    }
    if email_taken(email):
        raise ConflictError("Email já cadastrado")
    fields["role"] = _role(payload.get("role", DEFAULT_ROLE))
    return fields


def validate_user_changes(payload: dict, user_id: int, email_taken: Callable[[str, int], bool]) -> dict:
    changes = {}
    if "name" in payload:
        changes["name"] = _required_name(payload["name"])
    if "email" in payload:
        changes["email"] = _email(payload["email"])
        if email_taken(changes["email"], user_id):
            raise ConflictError("Email já cadastrado")
    if "password" in payload:
        changes["password"] = _password(payload["password"], "Senha muito curta")
    if "role" in payload:
        changes["role"] = _role(payload["role"])
    if "active" in payload:
        if not isinstance(payload["active"], bool):
            raise ValidationError("Campo active deve ser booleano")
        changes["active"] = payload["active"]
    return changes


def validate_credentials(payload: dict) -> tuple[str, str]:
    email, password = payload.get("email"), payload.get("password")
    if not (email and password and isinstance(email, str) and isinstance(password, str)):
        raise ValidationError("Email e senha são obrigatórios")
    return email, password


# --- categories

def validate_new_category(payload: dict) -> dict:
    return {
        "name": _required_name(payload.get("name")),
        "description": _optional_text(payload.get("description", ""), "Descrição inválida"),
        "color": _color(payload.get("color", DEFAULT_COLOR)),
    }


def validate_category_changes(payload: dict) -> dict:
    validators = {
        "name": _required_name,
        "description": lambda value: _optional_text(value, "Descrição inválida"),
        "color": _color,
    }
    return {field: validate(payload[field]) for field, validate in validators.items() if field in payload}


# --- field rules

def _title(value) -> str:
    if not isinstance(value, str):
        raise ValidationError("Título inválido")
    if len(value) < MIN_TITLE_LENGTH:
        raise ValidationError("Título muito curto")
    if len(value) > MAX_TITLE_LENGTH:
        raise ValidationError("Título muito longo")
    return value


def _optional_text(value, message: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ValidationError(message)
    return value


def _status(value) -> str:
    if value not in VALID_STATUSES:
        raise ValidationError("Status inválido")
    return value


def _priority(value) -> int:
    is_integer = isinstance(value, int) and not isinstance(value, bool)
    if not is_integer or not MIN_PRIORITY <= value <= MAX_PRIORITY:
        raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")
    return value


def _reference(value, exists: ExistsCheck, not_found_message: str) -> int | None:
    if not value:
        return None
    reference_id = _as_id(value)
    if reference_id is None or not exists(reference_id):
        raise NotFoundError(not_found_message)
    return reference_id


def _as_id(value) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _due_date(value, message: str) -> datetime | None:
    if not value:
        return None
    if not isinstance(value, str):
        raise ValidationError(message)
    try:
        return Task.parse_due_date(value)
    except ValueError as exc:
        raise ValidationError(message) from exc


def _tags(value) -> str | None:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(tag, str) for tag in value):
        return Task.join_tags(value)
    raise ValidationError("Tags inválidas")


def _query_int(raw: str, message: str) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError(message) from exc


def _name(value) -> str:
    if not isinstance(value, str):
        raise ValidationError("Nome inválido")
    return value


def _required_name(value) -> str:
    if not value:
        raise ValidationError("Nome é obrigatório")
    return _name(value)


def _email(value) -> str:
    if not isinstance(value, str) or not EMAIL_PATTERN.match(value):
        raise ValidationError("Email inválido")
    return value


def _password(value, too_short_message: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("Senha inválida")
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(too_short_message)
    return value


def _role(value) -> str:
    if value not in VALID_ROLES:
        raise ValidationError("Role inválido")
    return value


def _color(value) -> str:
    if not isinstance(value, str) or not COLOR_PATTERN.match(value):
        raise ValidationError("Cor inválida. Use o formato #RRGGBB")
    return value
