"""Validadores genéricos, sem dependência de framework ou banco."""
import re

from src.utils.errors import ValidationError

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')
INVALID_PAYLOAD_MESSAGE = 'Dados inválidos'


def require_json_object(payload, *, allow_empty: bool = False) -> dict:
    """Garante que o corpo da requisição é um objeto JSON."""
    if not isinstance(payload, dict) or not (payload or allow_empty):
        raise ValidationError(INVALID_PAYLOAD_MESSAGE)
    return payload


def validate_bounded_text(value, max_length: int, *, invalid_message: str, too_long_message: str) -> str:
    """Texto obrigatório que precisa caber no limite da coluna."""
    if not isinstance(value, str):
        raise ValidationError(invalid_message)
    if len(value) > max_length:
        raise ValidationError(too_long_message)
    return value


def validate_required_text(value, max_length: int, *, required_message: str, invalid_message: str,
                           too_long_message: str) -> str:
    """Texto obrigatório: além do tipo e do limite, não pode ser vazio nem só espaços."""
    text = validate_bounded_text(value, max_length, invalid_message=invalid_message,
                                 too_long_message=too_long_message)
    if not text.strip():
        raise ValidationError(required_message)
    return text


def validate_optional_bounded_text(value, max_length: int, *, invalid_message: str,
                                   too_long_message: str):
    """Mesma regra de `validate_bounded_text`, aceitando ausência de valor."""
    if value is None:
        return None
    return validate_bounded_text(value, max_length, invalid_message=invalid_message,
                                 too_long_message=too_long_message)


def is_valid_email(value) -> bool:
    return isinstance(value, str) and EMAIL_PATTERN.match(value) is not None


def is_integer(value) -> bool:
    """True para inteiros de verdade (booleanos não contam)."""
    return isinstance(value, int) and not isinstance(value, bool)


def ensure_optional_text(value, message: str):
    """Aceita texto ou ausência de valor; qualquer outro tipo é rejeitado."""
    if value is not None and not isinstance(value, str):
        raise ValidationError(message)
    return value
