"""Application settings read once from environment variables."""
import logging
import os
import secrets
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "sqlite:///tasks.db"  # relative SQLite paths live in Flask's instance/ folder
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
TRUE_VALUES = {"1", "true", "yes", "on"}


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in TRUE_VALUES


def _secret(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.warning("%s not set; using an ephemeral development value", name)
        value = secrets.token_hex(32)
    return value


def _origins(raw: str) -> str | list[str]:
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return "*" if not origins or "*" in origins else origins


@dataclass(frozen=True)
class Settings:
    secret_key: str
    debug: bool
    host: str
    port: int
    database_url: str
    cors_origins: str | list[str]
    log_level: str


def load_settings() -> Settings:
    return Settings(
        secret_key=_secret("SECRET_KEY"),
        debug=_bool("FLASK_DEBUG", False),
        host=os.environ.get("HOST", DEFAULT_HOST),
        port=int(os.environ.get("PORT", DEFAULT_PORT)),
        database_url=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        cors_origins=_origins(os.environ.get("CORS_ORIGINS", "*")),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )
