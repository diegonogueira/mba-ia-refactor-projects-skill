"""Validadores genéricos de entrada (sem dependência de framework ou banco)."""
from src.utils.errors import ValidationError


def require_json_object(payload, message: str = "Dados inválidos") -> dict:
    if not isinstance(payload, dict) or not payload:
        raise ValidationError(message)
    return payload


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_integer(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def parse_positive_int(value) -> int | None:
    """Aceita inteiro ou string só com dígitos (formatos que a API original aceitava para IDs)."""
    if isinstance(value, str) and value.isascii() and value.isdigit():
        value = int(value)
    if is_integer(value) and value > 0:
        return value
    return None


def parse_optional_float(value: str | None, message: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        raise ValidationError(message) from None
