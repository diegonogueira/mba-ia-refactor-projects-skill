"""Conversores de URL: `<int:...>` limitado ao maior inteiro do SQLite.

Um id acima do limite não corresponde à rota (404) em vez de chegar ao driver e virar OverflowError (500).
"""
from werkzeug.routing import IntegerConverter

from src.models.database import SQLITE_INT_MAX


class BoundedIntConverter(IntegerConverter):
    def __init__(self, url_map, fixed_digits=0, min=None, max=SQLITE_INT_MAX, signed=False):  # noqa: A002
        super().__init__(url_map, fixed_digits=fixed_digits, min=min, max=max, signed=signed)
