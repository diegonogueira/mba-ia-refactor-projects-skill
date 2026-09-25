"""Entidade Task: dados, regras de domínio e consultas."""
from collections import namedtuple
from datetime import datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import selectinload

from src.models.database import PersistableMixin, db
from src.utils.datetime_utils import utcnow_naive

TASK_STATUSES = ('pending', 'in_progress', 'done', 'cancelled')
DEFAULT_STATUS = 'pending'
DONE_STATUS = 'done'
CLOSED_STATUSES = ('done', 'cancelled')

MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_MAX = 2

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MAX_TAGS_LENGTH = 500
MAX_STATUS_LENGTH = 50
DUE_DATE_FORMAT = '%Y-%m-%d'
TAG_SEPARATOR = ','

# Mensagem de contrato da API para este recurso: controllers e validadores usam esta.
TASK_NOT_FOUND_MESSAGE = 'Task não encontrada'

UserTaskCounts = namedtuple('UserTaskCounts', ('total', 'completed'))
NO_TASKS = UserTaskCounts(0, 0)


class Task(PersistableMixin, db.Model):
    __tablename__ = 'tasks'

    CREATE_ERROR_MESSAGE = 'Erro ao criar task'
    NOT_FOUND_MESSAGE = TASK_NOT_FOUND_MESSAGE

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(MAX_TITLE_LENGTH), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(MAX_STATUS_LENGTH), default=DEFAULT_STATUS)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)
    updated_at = db.Column(db.DateTime, default=utcnow_naive, onupdate=utcnow_naive)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(MAX_TAGS_LENGTH), nullable=True)

    user = db.relationship('User', back_populates='tasks')
    category = db.relationship('Category', back_populates='tasks')

    # --- regras de domínio -------------------------------------------------

    @hybrid_method
    def is_overdue(self, now: datetime | None = None) -> bool:
        """Task vencida: tem prazo no passado e ainda não foi concluída nem cancelada."""
        now = now or utcnow_naive()
        return self.due_date is not None and self.due_date < now and self.status not in CLOSED_STATUSES

    @is_overdue.expression
    def is_overdue(cls, now: datetime | None = None):
        """Mesma regra, avaliada no banco (usada em contagens e filtros)."""
        now = now or utcnow_naive()
        return and_(cls.due_date.isnot(None), cls.due_date < now, cls.status.notin_(CLOSED_STATUSES))

    @hybrid_method
    def is_high_priority(self) -> bool:
        return self.priority is not None and self.priority <= HIGH_PRIORITY_MAX

    @is_high_priority.expression
    def is_high_priority(cls):
        """Mesma regra, avaliada no banco (usada nas contagens do relatório por usuário)."""
        return and_(cls.priority.isnot(None), cls.priority <= HIGH_PRIORITY_MAX)

    def days_overdue(self, now: datetime | None = None) -> int:
        now = now or utcnow_naive()
        return (now - self.due_date).days

    @property
    def tag_list(self) -> list[str]:
        return self.tags.split(TAG_SEPARATOR) if self.tags else []

    @staticmethod
    def encode_tags(tags):
        """Guarda as tags como texto separado por vírgula (formato original da coluna)."""
        return TAG_SEPARATOR.join(tags) if isinstance(tags, list) else tags

    def assign(self, fields: dict) -> None:
        super().assign({name: self.encode_tags(value) if name == 'tags' else value
                        for name, value in fields.items()})

    def update(self) -> None:
        self.updated_at = utcnow_naive()
        super().update()

    # --- consultas ---------------------------------------------------------

    @classmethod
    def list_all(cls, *, with_relations: bool = False) -> list['Task']:
        query = select(cls).order_by(cls.id)
        if with_relations:
            query = query.options(selectinload(cls.user), selectinload(cls.category))
        return list(db.session.execute(query).scalars())

    @classmethod
    def list_by_user(cls, user_id) -> list['Task']:
        return list(db.session.execute(select(cls).where(cls.user_id == user_id).order_by(cls.id)).scalars())

    @classmethod
    def search(cls, *, term: str = '', status: str = '', priority=None, user_id=None) -> list['Task']:
        query = select(cls)
        if term:
            pattern = f'%{term}%'
            query = query.where(or_(cls.title.like(pattern), cls.description.like(pattern)))
        if status:
            query = query.where(cls.status == status)
        if priority is not None:
            query = query.where(cls.priority == priority)
        if user_id is not None:
            query = query.where(cls.user_id == user_id)
        return list(db.session.execute(query.order_by(cls.id)).scalars())

    @classmethod
    def list_overdue(cls, now: datetime | None = None) -> list['Task']:
        return list(db.session.execute(select(cls).where(cls.is_overdue(now)).order_by(cls.id)).scalars())

    @classmethod
    def _scoped(cls, query, user_id):
        """Restringe a consulta a um usuário quando `user_id` é informado."""
        return query if user_id is None else query.where(cls.user_id == user_id)

    @classmethod
    def count_all(cls, *, user_id=None) -> int:
        return db.session.scalar(cls._scoped(select(func.count(cls.id)), user_id))

    @classmethod
    def count_overdue(cls, now: datetime | None = None, *, user_id=None) -> int:
        return db.session.scalar(cls._scoped(select(func.count(cls.id)).where(cls.is_overdue(now)), user_id))

    @classmethod
    def count_high_priority(cls, *, user_id=None) -> int:
        return db.session.scalar(cls._scoped(select(func.count(cls.id)).where(cls.is_high_priority()), user_id))

    @classmethod
    def count_by_status(cls, *, user_id=None) -> dict[str, int]:
        query = cls._scoped(select(cls.status, func.count(cls.id)), user_id).group_by(cls.status)
        counts = dict(db.session.execute(query).all())
        return {status: counts.get(status, 0) for status in TASK_STATUSES}

    @classmethod
    def count_by_priority(cls) -> dict[int, int]:
        counts = dict(db.session.execute(select(cls.priority, func.count(cls.id)).group_by(cls.priority)).all())
        return {priority: counts.get(priority, 0) for priority in range(MIN_PRIORITY, MAX_PRIORITY + 1)}

    @classmethod
    def count_by_category(cls) -> dict[int, int]:
        return dict(db.session.execute(select(cls.category_id, func.count(cls.id)).group_by(cls.category_id)).all())

    @classmethod
    def count_by_user(cls) -> dict[int, UserTaskCounts]:
        """Total e concluídas por usuário, em uma única consulta agregada."""
        rows = db.session.execute(
            select(cls.user_id,
                   func.count(cls.id),
                   func.sum(case((cls.status == DONE_STATUS, 1), else_=0)))
            .group_by(cls.user_id)
        ).all()
        return {user_id: UserTaskCounts(total, completed or 0) for user_id, total, completed in rows}

    @classmethod
    def count_created_since(cls, since: datetime) -> int:
        return db.session.scalar(select(func.count(cls.id)).where(cls.created_at >= since))

    @classmethod
    def count_completed_since(cls, since: datetime) -> int:
        return db.session.scalar(
            select(func.count(cls.id)).where(cls.status == DONE_STATUS, cls.updated_at >= since)
        )
