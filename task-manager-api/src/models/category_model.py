"""Entidade Category: dados e consultas."""
from sqlalchemy import func, select

from src.models.database import PersistableMixin, db
from src.utils.datetime_utils import utcnow_naive

DEFAULT_COLOR = '#000000'
COLOR_LENGTH = 7


class Category(PersistableMixin, db.Model):
    __tablename__ = 'categories'

    CREATE_ERROR_MESSAGE = 'Erro ao criar categoria'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
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
