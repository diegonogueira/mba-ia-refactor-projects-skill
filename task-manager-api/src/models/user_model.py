"""Entidade User: dados, credenciais e consultas."""
from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from src.models.database import PersistableMixin, db
from src.utils.datetime_utils import utcnow_naive

DEFAULT_ROLE = 'user'
ADMIN_ROLE = 'admin'
MANAGER_ROLE = 'manager'
USER_ROLES = (DEFAULT_ROLE, ADMIN_ROLE, MANAGER_ROLE)
# Papéis que um cliente anônimo pode pedir para si; os demais só por uma rota administrativa autenticada.
SELF_SIGNUP_ROLES = (DEFAULT_ROLE,)
MIN_PASSWORD_LENGTH = 8
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 150
MAX_ROLE_LENGTH = 50
# `generate_password_hash` devolve ~162 caracteres com scrypt; a folga cobre trocas de algoritmo
MAX_PASSWORD_HASH_LENGTH = 255

# Mensagem de contrato da API para este recurso: controllers, validadores e services usam esta.
USER_NOT_FOUND_MESSAGE = 'Usuário não encontrado'


class User(PersistableMixin, db.Model):
    __tablename__ = 'users'

    CREATE_ERROR_MESSAGE = 'Erro ao criar usuário'
    NOT_FOUND_MESSAGE = USER_NOT_FOUND_MESSAGE

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(MAX_NAME_LENGTH), nullable=False)
    email = db.Column(db.String(MAX_EMAIL_LENGTH), unique=True, nullable=False)
    password = db.Column(db.String(MAX_PASSWORD_HASH_LENGTH), nullable=False)
    role = db.Column(db.String(MAX_ROLE_LENGTH), default=DEFAULT_ROLE)
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

    # --- autorização ------------------------------------------------------

    @property
    def is_admin(self) -> bool:
        return self.role == ADMIN_ROLE

    def can_act_for(self, user_id) -> bool:
        """Pode ler/alterar dados do usuário `user_id`: é o próprio, é admin, ou o dado não tem dono."""
        return user_id is None or self.is_admin or user_id == self.id

    @classmethod
    def register(cls, *, name: str, email: str, password: str, role: str = DEFAULT_ROLE) -> 'User':
        user = cls(name=name, email=email, role=role)
        user.set_password(password)
        user.create()
        return user

    # --- consultas ---------------------------------------------------------

    @classmethod
    def get_by_email(cls, email: str) -> 'User | None':
        return db.session.execute(select(cls).where(cls.email == email)).scalar_one_or_none()

    @classmethod
    def email_in_use(cls, email: str, *, exclude_id=None) -> bool:
        user = cls.get_by_email(email)
        return user is not None and user.id != exclude_id
