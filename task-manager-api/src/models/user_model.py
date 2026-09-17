import hashlib
import hmac
import logging

from werkzeug.security import check_password_hash, generate_password_hash

from src.models.database import PersistenceMixin, commit, db
from src.utils.dates import utc_now
from src.utils.errors import PersistenceError

logger = logging.getLogger(__name__)

VALID_ROLES = ("user", "admin", "manager")
DEFAULT_ROLE = "user"
MIN_PASSWORD_LENGTH = 4
HASH_FIELD_SEPARATOR = "$"  # werkzeug hashes look like "scrypt:...$salt$hash"; legacy MD5 hex digests have no separator


class User(PersistenceMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default=DEFAULT_ROLE)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # deleting a user also deletes the tasks assigned to them
    tasks = db.relationship("Task", back_populates="user", cascade="save-update, merge, delete")

    # --- password rules

    def set_password(self, raw_password: str) -> None:
        self.password = generate_password_hash(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        if HASH_FIELD_SEPARATOR in self.password:
            return check_password_hash(self.password, raw_password)
        return self._verify_legacy_password(raw_password)

    def _verify_legacy_password(self, raw_password: str) -> bool:
        """Accept rows hashed with the old unsalted MD5 once and upgrade them to a salted hash."""
        legacy_digest = hashlib.md5(raw_password.encode()).hexdigest()
        if not hmac.compare_digest(self.password, legacy_digest):
            return False
        self.set_password(raw_password)
        try:
            commit("Erro ao atualizar hash de senha")
        except PersistenceError:
            logger.warning("Could not upgrade legacy password hash for user id=%s", self.id)
        return True

    # --- persistence

    @classmethod
    def create(cls, fields: dict, error_message: str) -> "User":
        user = cls(**{field: value for field, value in fields.items() if field != "password"})
        user.set_password(fields["password"])
        user.save(error_message)
        return user

    def update(self, changes: dict, error_message: str) -> None:
        changes = dict(changes)
        if "password" in changes:
            self.set_password(changes.pop("password"))
        super().update(changes, error_message)

    # --- queries

    @classmethod
    def find_by_email(cls, email: str) -> "User | None":
        return db.session.execute(db.select(cls).where(cls.email == email)).scalar_one_or_none()

    @classmethod
    def email_taken(cls, email: str, exclude_user_id: int | None = None) -> bool:
        existing = cls.find_by_email(email)
        return existing is not None and existing.id != exclude_user_id
