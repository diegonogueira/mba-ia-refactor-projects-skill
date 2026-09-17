"""Validação dos payloads de categoria."""
from src.models.category_model import DEFAULT_COLOR
from src.utils.errors import ValidationError
from src.utils.validators import ensure_optional_text, require_json_object

NAME_REQUIRED_MESSAGE = 'Nome é obrigatório'
NAME_INVALID_MESSAGE = 'Nome inválido'
DESCRIPTION_INVALID_MESSAGE = 'Descrição inválida'
COLOR_INVALID_MESSAGE = 'Cor inválida'

TEXT_FIELDS = (('description', DESCRIPTION_INVALID_MESSAGE), ('color', COLOR_INVALID_MESSAGE))


def _name(value) -> str:
    if not isinstance(value, str):
        raise ValidationError(NAME_INVALID_MESSAGE)
    return value


def validate_new_category(payload) -> dict:
    data = require_json_object(payload)

    name = data.get('name')
    if not name:
        raise ValidationError(NAME_REQUIRED_MESSAGE)

    fields = {'name': _name(name), 'description': data.get('description', ''),
              'color': data.get('color', DEFAULT_COLOR)}
    for field, message in TEXT_FIELDS:
        ensure_optional_text(fields[field], message)
    return fields


def validate_category_changes(payload) -> dict:
    # a rota original aceitava corpo vazio nesta atualização (nenhum campo alterado)
    data = require_json_object(payload, allow_empty=True)

    changes = {}
    if 'name' in data:
        changes['name'] = _name(data['name'])
    for field, message in TEXT_FIELDS:
        if field in data:
            changes[field] = ensure_optional_text(data[field], message)
    return changes
