"""Validação dos payloads de task: mesmas mensagens e mesma ordem de checagem da API original."""
from datetime import datetime

from src.models.category_model import CATEGORY_NOT_FOUND_MESSAGE
from src.models.task_model import (DEFAULT_PRIORITY, DEFAULT_STATUS, DUE_DATE_FORMAT, MAX_PRIORITY,
                                   MAX_TAGS_LENGTH, MAX_TITLE_LENGTH, MIN_PRIORITY, MIN_TITLE_LENGTH,
                                   TASK_STATUSES, Task)
from src.models.user_model import USER_NOT_FOUND_MESSAGE
from src.utils.errors import NotFoundError, ValidationError
from src.utils.validators import (ensure_optional_text, is_integer, require_json_object,
                                  validate_required_text)

TITLE_REQUIRED_MESSAGE = 'Título é obrigatório'
TITLE_INVALID_MESSAGE = 'Título inválido'
TITLE_TOO_SHORT_MESSAGE = 'Título muito curto'
TITLE_TOO_LONG_MESSAGE = 'Título muito longo'
STATUS_INVALID_MESSAGE = 'Status inválido'
PRIORITY_INVALID_MESSAGE = 'Prioridade inválida'
PRIORITY_RANGE_MESSAGE = 'Prioridade deve ser entre 1 e 5'
DESCRIPTION_INVALID_MESSAGE = 'Descrição inválida'
TAGS_INVALID_MESSAGE = 'Tags inválidas'
TAGS_TOO_LONG_MESSAGE = 'Tags muito longas'
USER_INVALID_MESSAGE = 'user_id inválido'
CATEGORY_INVALID_MESSAGE = 'category_id inválido'
DUE_DATE_ON_CREATE_MESSAGE = 'Formato de data inválido. Use YYYY-MM-DD'
DUE_DATE_ON_UPDATE_MESSAGE = 'Formato de data inválido'


def _title(value) -> str:
    title = validate_required_text(value, MAX_TITLE_LENGTH, required_message=TITLE_REQUIRED_MESSAGE,
                                   invalid_message=TITLE_INVALID_MESSAGE, too_long_message=TITLE_TOO_LONG_MESSAGE)
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError(TITLE_TOO_SHORT_MESSAGE)
    return title


def _status(value) -> str:
    if value not in TASK_STATUSES:
        raise ValidationError(STATUS_INVALID_MESSAGE)
    return value


def _priority(value) -> int:
    if not is_integer(value):
        raise ValidationError(PRIORITY_INVALID_MESSAGE)
    if not MIN_PRIORITY <= value <= MAX_PRIORITY:
        raise ValidationError(PRIORITY_RANGE_MESSAGE)
    return value


def _reference(value, exists, not_found_message: str, invalid_message: str):
    """Id opcional de outra entidade: vazio vira None, preenchido precisa existir."""
    if not value:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValidationError(invalid_message)
    if isinstance(value, str):
        if not value.isdigit():
            raise NotFoundError(not_found_message)
        value = int(value)
    if not exists(value):
        raise NotFoundError(not_found_message)
    return value


def _due_date(value, message: str) -> datetime:
    try:
        return datetime.strptime(value, DUE_DATE_FORMAT)
    except (TypeError, ValueError):
        raise ValidationError(message) from None


def _tags(value):
    if isinstance(value, list):
        if not all(isinstance(tag, str) for tag in value):
            raise ValidationError(TAGS_INVALID_MESSAGE)
    elif value is not None and not isinstance(value, str):
        raise ValidationError(TAGS_INVALID_MESSAGE)
    # a coluna guarda as tags unidas por vírgula: o limite vale para essa string final
    if value is not None and len(Task.encode_tags(value)) > MAX_TAGS_LENGTH:
        raise ValidationError(TAGS_TOO_LONG_MESSAGE)
    return value


def validate_new_task(payload, *, user_exists, category_exists) -> dict:
    data = require_json_object(payload)

    title = data.get('title')
    if not title:
        raise ValidationError(TITLE_REQUIRED_MESSAGE)

    due_date = data.get('due_date')
    tags = data.get('tags')
    return {
        'title': _title(title),
        'status': _status(data.get('status', DEFAULT_STATUS)),
        'priority': _priority(data.get('priority', DEFAULT_PRIORITY)),
        'user_id': _reference(data.get('user_id'), user_exists, USER_NOT_FOUND_MESSAGE, USER_INVALID_MESSAGE),
        'category_id': _reference(data.get('category_id'), category_exists,
                                  CATEGORY_NOT_FOUND_MESSAGE, CATEGORY_INVALID_MESSAGE),
        'due_date': _due_date(due_date, DUE_DATE_ON_CREATE_MESSAGE) if due_date else None,
        'tags': _tags(tags) if tags else None,
        'description': ensure_optional_text(data.get('description', ''), DESCRIPTION_INVALID_MESSAGE),
    }


def validate_task_changes(payload, *, user_exists, category_exists) -> dict:
    data = require_json_object(payload)
    changes = {}

    if 'title' in data:
        changes['title'] = _title(data['title'])
    if 'status' in data:
        changes['status'] = _status(data['status'])
    if 'priority' in data:
        changes['priority'] = _priority(data['priority'])
    if 'user_id' in data:
        changes['user_id'] = _reference(data['user_id'], user_exists,
                                        USER_NOT_FOUND_MESSAGE, USER_INVALID_MESSAGE)
    if 'category_id' in data:
        changes['category_id'] = _reference(data['category_id'], category_exists,
                                            CATEGORY_NOT_FOUND_MESSAGE, CATEGORY_INVALID_MESSAGE)
    if 'due_date' in data:
        changes['due_date'] = _due_date(data['due_date'], DUE_DATE_ON_UPDATE_MESSAGE) if data['due_date'] else None
    if 'tags' in data:
        changes['tags'] = _tags(data['tags'])
    if 'description' in data:
        changes['description'] = ensure_optional_text(data['description'], DESCRIPTION_INVALID_MESSAGE)
    return changes


def parse_search_filters(args) -> dict:
    return {
        'term': args.get('q', ''),
        'status': args.get('status', ''),
        'priority': _int_param(args.get('priority', ''), 'priority'),
        'user_id': _int_param(args.get('user_id', ''), 'user_id'),
    }


def _int_param(value: str, name: str):
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError(f'Parâmetro {name} inválido') from None
