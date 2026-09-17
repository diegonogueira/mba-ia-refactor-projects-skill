"""Configuração da aplicação lida de variáveis de ambiente, com defaults seguros."""
import logging
import os
import secrets
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _secret(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.warning("%s não definida; usando um valor efêmero de desenvolvimento", name)
        value = secrets.token_hex(32)
    return value


def _origins(raw: str) -> str | list[str]:
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return "*" if origins in ([], ["*"]) else origins


@dataclass(frozen=True)
class Settings:
    secret_key: str
    debug: bool
    host: str
    port: int
    database_path: str
    seed_database: bool
    cors_origins: str | list[str]
    app_env: str
    admin_endpoints_enabled: bool
    admin_token: str | None


def load_settings() -> Settings:
    return Settings(
        secret_key=_secret("SECRET_KEY"),
        debug=_bool("FLASK_DEBUG", False),
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5000")),
        database_path=os.environ.get("DATABASE_PATH", "loja.db"),
        seed_database=_bool("SEED_DATABASE", True),
        cors_origins=_origins(os.environ.get("CORS_ORIGINS", "*")),
        app_env=os.environ.get("APP_ENV", "producao"),
        admin_endpoints_enabled=_bool("ADMIN_ENDPOINTS_ENABLED", False),
        admin_token=os.environ.get("ADMIN_TOKEN") or None,
    )
