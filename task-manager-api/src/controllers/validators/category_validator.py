"""Validação dos payloads de categoria."""
from src.models.category_model import (COLOR_PATTERN, DEFAULT_COLOR, MAX_DESCRIPTION_LENGTH,
                                       MAX_NAME_LENGTH)
from src.utils.errors import ValidationError
from src.utils.validators import (require_json_object, validate_optional_bounded_text,
                                  validate_required_text)

NAME_REQUIRED_MESSAGE = 'Nome é obrigatório'
NAME_INVALID_MESSAGE = 'Nome inválido'
NAME_TOO_LONG_MESSAGE = 'Nome muito longo'
DESCRIPTION_INVALID_MESSAGE = 'Descrição inválida'
DESCRIPTION_TOO_LONG_MESSAGE = 'Descrição muito longa'
COLOR_INVALID_MESSAGE = 'Cor inválida'


def _name(value) -> str:
    return validate_required_text(value, MAX_NAME_LENGTH, required_message=NAME_REQUIRED_MESSAGE,
                                  invalid_message=NAME_INVALID_MESSAGE, too_long_message=NAME_TOO_LONG_MESSAGE)


def _description(value):
    return validate_optional_bounded_text(value, MAX_DESCRIPTION_LENGTH,
                                          invalid_message=DESCRIPTION_INVALID_MESSAGE,
                                          too_long_message=DESCRIPTION_TOO_LONG_MESSAGE)


def _color(value):
    """Cor precisa caber na coluna: hexadecimal no formato #RRGGBB."""
    if value is not None and (not isinstance(value, str) or not COLOR_PATTERN.match(value)):
        raise ValidationError(COLOR_INVALID_MESSAGE)
    return value


def validate_new_category(payload) -> dict:
    data = require_json_object(payload)

    name = data.get('name')
    if not name:
        raise ValidationError(NAME_REQUIRED_MESSAGE)

    return {
        'name': _name(name),
        'description': _description(data.get('description', '')),
        'color': _color(data.get('color', DEFAULT_COLOR)),
    }


def validate_category_changes(payload) -> dict:
    # a rota original aceitava corpo vazio nesta atualização (nenhum campo alterado)
    data = require_json_object(payload, allow_empty=True)

    changes = {}
    if 'name' in data:
        changes['name'] = _name(data['name'])
    if 'description' in data:
        changes['description'] = _description(data['description'])
    if 'color' in data:
        changes['color'] = _color(data['color'])
    return changes
