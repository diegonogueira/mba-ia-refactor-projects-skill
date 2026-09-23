"""Configurações da aplicação lidas de variáveis de ambiente.

Convenção de nomes: módulos de infraestrutura (config, conexão, middlewares, erros) usam identificadores
em inglês; o domínio (models, services, controllers, views) usa português.
"""
import logging
import os
import secrets
from dataclasses import dataclass

logger = logging.getLogger(__name__)

API_VERSION = "1.0.0"

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
DEFAULT_DATABASE_PATH = "loja.db"
DEFAULT_APP_ENV = "producao"
# Validade do token emitido pelo /login.
DEFAULT_TOKEN_MAX_AGE_SECONDS = 8 * 60 * 60
SECRET_BYTES = 32
TRUTHY = {"1", "true", "yes", "on"}


def configure_logging(level=None):
    """Configura o logging da aplicação.

    Fica aqui (e não só no `python app.py`) para que servidores WSGI que importam
    `create_app()` também tenham os logs da aplicação. `basicConfig` é idempotente:
    não faz nada quando a raiz já tem handlers.
    """
    logging.basicConfig(level=level or os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(), format=LOG_FORMAT)


def _flag(name, default):
    return os.environ.get(name, str(default)).strip().lower() in TRUTHY


def _secret(name):
    value = os.environ.get(name)
    if not value:
        logger.warning("%s não definido; usando valor efêmero (tokens de login deixam de valer a cada boot)", name)
        value = secrets.token_hex(SECRET_BYTES)
    return value


def _csv_list(name, default):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


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
    token_max_age: int


def load_settings():
    host = os.environ.get("HOST", DEFAULT_HOST)
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    # Padrão: libera apenas a própria aplicação (mesmo host e porta). Use CORS_ORIGINS para abrir outras.
    default_origin = f"http://{host}:{port}"
    return Settings(
        secret_key=_secret("SECRET_KEY"),
        debug=_flag("FLASK_DEBUG", False),
        host=host,
        port=port,
        database_path=os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH),
        cors_origins=_csv_list("CORS_ORIGINS", default_origin),
        app_env=os.environ.get("APP_ENV", DEFAULT_APP_ENV),
        seed_database=_flag("SEED_DATABASE", True),
        seed_password=os.environ.get("SEED_PASSWORD") or None,
        admin_endpoints_enabled=_flag("ADMIN_ENDPOINTS_ENABLED", False),
        admin_token=os.environ.get("ADMIN_TOKEN") or None,
        token_max_age=int(os.environ.get("TOKEN_MAX_AGE", DEFAULT_TOKEN_MAX_AGE_SECONDS)),
    )
