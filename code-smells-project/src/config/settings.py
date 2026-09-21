"""Configurações da aplicação lidas de variáveis de ambiente."""
import logging
import os
import secrets
from dataclasses import dataclass

logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"

FORMATO_LOG = "%(asctime)s %(levelname)s %(name)s: %(message)s"
NIVEL_LOG_PADRAO = "INFO"
# Origens liberadas por padrão: apenas a própria aplicação. Use CORS_ORIGINS para abrir outras.
CORS_ORIGINS_PADRAO = "http://127.0.0.1:5000"


def configure_logging(nivel=None):
    """Configura o logging da aplicação.

    Fica aqui (e não só no `python app.py`) para que servidores WSGI que importam
    `create_app()` também tenham os logs da aplicação. `basicConfig` é idempotente:
    não faz nada quando a raiz já tem handlers.
    """
    logging.basicConfig(level=nivel or os.environ.get("LOG_LEVEL", NIVEL_LOG_PADRAO).upper(), format=FORMATO_LOG)


def _bool(nome, padrao):
    return os.environ.get(nome, str(padrao)).strip().lower() in {"1", "true", "yes", "on"}


def _segredo(nome):
    valor = os.environ.get(nome)
    if not valor:
        logger.warning("%s não definido; usando valor efêmero de desenvolvimento", nome)
        valor = secrets.token_hex(32)
    return valor


def _lista(nome, padrao):
    return [item.strip() for item in os.environ.get(nome, padrao).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    secret_key: str
    debug: bool
    host: str
    port: int
    database_path: str
    cors_origins: list
    app_env: str
    seed_database: bool
    seed_password: str | None
    admin_endpoints_enabled: bool
    admin_token: str | None


def load_settings():
    return Settings(
        secret_key=_segredo("SECRET_KEY"),
        debug=_bool("FLASK_DEBUG", False),
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        database_path=os.environ.get("DATABASE_PATH", "loja.db"),
        cors_origins=_lista("CORS_ORIGINS", CORS_ORIGINS_PADRAO),
        app_env=os.environ.get("APP_ENV", "producao"),
        seed_database=_bool("SEED_DATABASE", True),
        seed_password=os.environ.get("SEED_PASSWORD") or None,
        admin_endpoints_enabled=_bool("ADMIN_ENDPOINTS_ENABLED", False),
        admin_token=os.environ.get("ADMIN_TOKEN") or None,
    )
