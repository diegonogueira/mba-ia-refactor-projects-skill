"""Helpers de data e hora."""
from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """Horário UTC atual sem tzinfo.

    Substitui `datetime.utcnow()` (deprecated desde o Python 3.12) mantendo o formato
    naive já gravado nas colunas DateTime e usado nas respostas da API.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
