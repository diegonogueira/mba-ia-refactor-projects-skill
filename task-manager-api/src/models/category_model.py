"""Entidade Category: dados e consultas."""
import re

from sqlalchemy import func, select

from src.models.database import PersistableMixin, db
from src.utils.datetime_utils import utcnow_naive

DEFAULT_COLOR = '#000000'
COLOR_LENGTH = 7
COLOR_PATTERN = re.compile(r'^#[0-9a-fA-F]{6}$')
MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 300

# Mensagem de contrato da API para este recurso: controllers e validadores usam esta.
CATEGORY_NOT_FOUND_MESSAGE = 'Categoria não encontrada'


class Category(PersistableMixin, db.Model):
    __tablename__ = 'categories'

    CREATE_ERROR_MESSAGE = 'Erro ao criar categoria'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(MAX_NAME_LENGTH), nullable=False)
    description = db.Column(db.String(MAX_DESCRIPTION_LENGTH), nullable=True)
    color = db.Column(db.String(COLOR_LENGTH), default=DEFAULT_COLOR)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    # apagar uma categoria mantém as tasks e zera o category_id delas (comportamento original)
    tasks = db.relationship('Task', back_populates='category')

    @classmethod
    def get_by_id(cls, category_id) -> 'Category | None':
        return db.session.get(cls, category_id)

    @classmethod
    def exists(cls, category_id) -> bool:
        return cls.get_by_id(category_id) is not None

    @classmethod
    def list_all(cls) -> list['Category']:
        return list(db.session.execute(select(cls).order_by(cls.id)).scalars())

    @classmethod
    def count_all(cls) -> int:
        return db.session.scalar(select(func.count(cls.id)))
