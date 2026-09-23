"""Conversores de URL: ids fora da faixa do banco não chegam ao model (respondem 404 como id inexistente)."""
from werkzeug.routing import IntegerConverter

from src.controllers.validators import INTEIRO_MAXIMO


class IdConverter(IntegerConverter):
    """`<int:...>` limitado ao maior inteiro que o SQLite armazena."""

    def __init__(self, url_map, *args, **kwargs):
        kwargs.setdefault("max", INTEIRO_MAXIMO)
        super().__init__(url_map, *args, **kwargs)
