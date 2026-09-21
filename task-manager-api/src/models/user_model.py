"""Entidade User: dados, credenciais e consultas."""
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from src.models.database import PersistableMixin, db
from src.utils.datetime_utils import utcnow_naive

USER_ROLES = ('user', 'admin', 'manager')
DEFAULT_ROLE = 'user'
# Papéis que um cliente anônimo pode pedir para si; os demais só por uma rota administrativa autenticada.
SELF_SIGNUP_ROLES = (DEFAULT_ROLE,)
MIN_PASSWORD_LENGTH = 8
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 150


class User(PersistableMixin, db.Model):
    __tablename__ = 'users'

    CREATE_ERROR_MESSAGE = 'Erro ao criar usuário'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(MAX_NAME_LENGTH), nullable=False)
    email = db.Column(db.String(MAX_EMAIL_LENGTH), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow_naive)

    # apagar um usuário apaga as tasks dele (comportamento original, agora na mesma transação)
    tasks = db.relationship('Task', back_populates='user', cascade='all, delete')

    # --- credenciais -------------------------------------------------------

    def set_password(self, raw_password: str) -> None:
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password, raw_password)

    def assign(self, fields: dict) -> None:
        password = fields.pop('password', None)
        super().assign(fields)
        if password is not None:
            self.set_password(password)

    @classmethod
    def register(cls, *, name: str, email: str, password: str, role: str = DEFAULT_ROLE) -> 'User':
        user = cls(name=name, email=email, role=role)
        user.set_password(password)
        user.create()
        return user

    # --- consultas ---------------------------------------------------------

    @classmethod
    def get_by_id(cls, user_id) -> 'User | None':
        return db.session.get(cls, user_id)

    @classmethod
    def get_by_email(cls, email: str) -> 'User | None':
        return db.session.execute(select(cls).where(cls.email == email)).scalar_one_or_none()

    @classmethod
    def exists(cls, user_id) -> bool:
        return cls.get_by_id(user_id) is not None

    @classmethod
    def email_in_use(cls, email: str, *, exclude_id=None) -> bool:
        user = cls.get_by_email(email)
        return user is not None and user.id != exclude_id

    @classmethod
    def list_all(cls) -> list['User']:
        return list(db.session.execute(select(cls).order_by(cls.id)).scalars())

    @classmethod
    def count_all(cls) -> int:
        return db.session.scalar(select(func.count(cls.id)))
