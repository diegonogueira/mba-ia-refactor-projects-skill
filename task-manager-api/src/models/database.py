"""Database extension, schema bootstrap and shared persistence helpers."""
import logging

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

from src.utils.errors import PersistenceError

logger = logging.getLogger(__name__)

db = SQLAlchemy()


def init_database(app) -> None:
    db.init_app(app)
    with app.app_context():
        db.create_all()


def commit(error_message: str) -> None:
    """Commit the current unit of work; roll back and raise PersistenceError on failure."""
    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.exception("Database commit failed")
        raise PersistenceError(error_message) from exc


class PersistenceMixin:
    """Common data access for entities with an integer `id` primary key."""

    @classmethod
    def find_by_id(cls, entity_id: int):
        return db.session.get(cls, entity_id)

    @classmethod
    def exists(cls, entity_id: int) -> bool:
        return cls.find_by_id(entity_id) is not None

    @classmethod
    def list_all(cls) -> list:
        return db.session.execute(db.select(cls).order_by(cls.id)).scalars().all()

    @classmethod
    def count(cls) -> int:
        return db.session.execute(db.select(db.func.count(cls.id))).scalar_one()

    @classmethod
    def create(cls, fields: dict, error_message: str):
        entity = cls(**fields)
        entity.save(error_message)
        return entity

    def save(self, error_message: str) -> None:
        db.session.add(self)
        commit(error_message)

    def update(self, changes: dict, error_message: str) -> None:
        for field, value in changes.items():
            setattr(self, field, value)
        commit(error_message)

    def delete(self, error_message: str) -> None:
        db.session.delete(self)
        commit(error_message)
