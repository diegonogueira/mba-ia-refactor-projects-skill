from datetime import datetime

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import joinedload

from src.models.database import PersistenceMixin, db
from src.utils.dates import utc_now

VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")
CLOSED_STATUSES = ("done", "cancelled")
DONE_STATUS = "done"
DEFAULT_STATUS = "pending"

MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_PRIORITY = 3
HIGH_PRIORITY_THRESHOLD = 2  # priorities 1 and 2 count as high priority
PRIORITY_LABELS = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}

MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 200
MAX_TAGS_LENGTH = 500
TAG_SEPARATOR = ","
DUE_DATE_FORMAT = "%Y-%m-%d"


class Task(PersistenceMixin, db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(MAX_TITLE_LENGTH), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default=DEFAULT_STATUS)
    priority = db.Column(db.Integer, default=DEFAULT_PRIORITY)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(MAX_TAGS_LENGTH), nullable=True)

    user = db.relationship("User", back_populates="tasks")
    category = db.relationship("Category", back_populates="tasks")

    # --- domain rules

    def is_overdue(self, now: datetime | None = None) -> bool:
        now = now or utc_now()
        return self.due_date is not None and self.due_date < now and self.status not in CLOSED_STATUSES

    @property
    def tag_list(self) -> list[str]:
        return self.tags.split(TAG_SEPARATOR) if self.tags else []

    @staticmethod
    def join_tags(tags: list[str] | str | None) -> str | None:
        return TAG_SEPARATOR.join(tags) if isinstance(tags, list) else tags

    @staticmethod
    def parse_due_date(value: str) -> datetime:
        return datetime.strptime(value, DUE_DATE_FORMAT)

    # --- persistence

    def update(self, changes: dict, error_message: str) -> None:
        super().update({**changes, "updated_at": utc_now()}, error_message)

    # --- queries

    @classmethod
    def list_with_relations(cls) -> list["Task"]:
        query = db.select(cls).options(joinedload(cls.user), joinedload(cls.category)).order_by(cls.id)
        return db.session.execute(query).scalars().all()

    @classmethod
    def list_by_user(cls, user_id: int) -> list["Task"]:
        query = db.select(cls).where(cls.user_id == user_id).order_by(cls.id)
        return db.session.execute(query).scalars().all()

    @classmethod
    def search(cls, text: str = "", status: str = "", priority: int | None = None,
               user_id: int | None = None) -> list["Task"]:
        query = db.select(cls)
        if text:
            pattern = f"%{text}%"
            query = query.where(or_(cls.title.like(pattern), cls.description.like(pattern)))
        if status:
            query = query.where(cls.status == status)
        if priority is not None:
            query = query.where(cls.priority == priority)
        if user_id is not None:
            query = query.where(cls.user_id == user_id)
        return db.session.execute(query.order_by(cls.id)).scalars().all()

    @classmethod
    def _overdue_condition(cls, now: datetime):
        return and_(cls.due_date.is_not(None), cls.due_date < now, cls.status.not_in(CLOSED_STATUSES))

    @classmethod
    def list_overdue(cls, now: datetime) -> list["Task"]:
        query = db.select(cls).where(cls._overdue_condition(now)).order_by(cls.id)
        return db.session.execute(query).scalars().all()

    @classmethod
    def _count(cls, *conditions) -> int:
        return db.session.execute(db.select(func.count(cls.id)).where(*conditions)).scalar_one()

    @classmethod
    def count(cls, user_id: int | None = None) -> int:
        return cls._count(cls.user_id == user_id) if user_id is not None else cls._count()

    @classmethod
    def count_overdue(cls, now: datetime, user_id: int | None = None) -> int:
        conditions = [cls._overdue_condition(now)]
        if user_id is not None:
            conditions.append(cls.user_id == user_id)
        return cls._count(*conditions)

    @classmethod
    def count_high_priority(cls, user_id: int) -> int:
        return cls._count(cls.user_id == user_id, cls.priority <= HIGH_PRIORITY_THRESHOLD)

    @classmethod
    def count_created_since(cls, since: datetime) -> int:
        return cls._count(cls.created_at >= since)

    @classmethod
    def count_completed_since(cls, since: datetime) -> int:
        return cls._count(cls.status == DONE_STATUS, cls.updated_at >= since)

    @classmethod
    def count_by_status(cls, user_id: int | None = None) -> dict[str, int]:
        query = db.select(cls.status, func.count(cls.id)).group_by(cls.status)
        if user_id is not None:
            query = query.where(cls.user_id == user_id)
        return dict(db.session.execute(query).all())

    @classmethod
    def count_by_priority(cls) -> dict[int, int]:
        query = db.select(cls.priority, func.count(cls.id)).group_by(cls.priority)
        return dict(db.session.execute(query).all())

    @classmethod
    def count_by_category(cls) -> dict[int, int]:
        query = db.select(cls.category_id, func.count(cls.id)).group_by(cls.category_id)
        return dict(db.session.execute(query).all())

    @classmethod
    def count_by_user(cls) -> dict[int, tuple[int, int]]:
        """user_id -> (total tasks, done tasks)."""
        done = func.sum(case((cls.status == DONE_STATUS, 1), else_=0))
        query = db.select(cls.user_id, func.count(cls.id), done).group_by(cls.user_id)
        return {user_id: (total, done_count or 0) for user_id, total, done_count in db.session.execute(query).all()}
