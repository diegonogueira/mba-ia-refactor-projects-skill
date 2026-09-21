"""Configurações da aplicação, lidas uma única vez de variáveis de ambiente (com defaults seguros)."""
import logging
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATABASE_URL = 'sqlite:///tasks.db'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 5000
# Origens de desenvolvimento; liberar qualquer origem exige CORS_ORIGINS=* explícito no ambiente.
DEFAULT_CORS_ORIGINS = 'http://localhost:3000,http://127.0.0.1:3000'
DEFAULT_LOG_LEVEL = 'INFO'
TRUTHY_VALUES = {'1', 'true', 'yes', 'on'}


@dataclass(frozen=True)
class Settings:
    secret_key: str
    database_url: str
    debug: bool
    host: str
    port: int
    cors_origins: str | list[str]
    log_level: str


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in TRUTHY_VALUES


def _secret(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.warning('%s não definida; usando um valor efêmero de desenvolvimento', name)
        value = secrets.token_hex(32)
    return value


def _cors_origins(raw: str) -> str | list[str]:
    origins = [origin.strip() for origin in raw.split(',') if origin.strip()]
    if not origins:
        return _cors_origins(DEFAULT_CORS_ORIGINS)
    if origins == ['*']:
        logger.warning('CORS_ORIGINS=* libera a API para qualquer origem; use apenas em desenvolvimento')
        return '*'
    return origins


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / '.env')
    return Settings(
        secret_key=_secret('SECRET_KEY'),
        database_url=os.environ.get('DATABASE_URL', DEFAULT_DATABASE_URL),
        debug=_bool('FLASK_DEBUG', False),
        host=os.environ.get('HOST', DEFAULT_HOST),
        port=int(os.environ.get('PORT', DEFAULT_PORT)),
        cors_origins=_cors_origins(os.environ.get('CORS_ORIGINS', DEFAULT_CORS_ORIGINS)),
        log_level=os.environ.get('LOG_LEVEL', DEFAULT_LOG_LEVEL).upper(),
    )
