"""Sessão do banco, bootstrap do schema e persistência compartilhada pelas entidades."""
import logging

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

from src.utils.errors import PersistenceError

logger = logging.getLogger(__name__)

db = SQLAlchemy()

# O texto de um erro do SQLAlchemy embute o SQL e os valores ligados (inclusive hashes de senha);
# `hide_parameters` mantém esses valores fora de qualquer log ou traceback.
ENGINE_OPTIONS = {'hide_parameters': True}


def init_database(app) -> None:
    """Liga a extensão à aplicação e garante o schema (chamado pelo composition root)."""
    db.init_app(app)
    with app.app_context():
        db.create_all()


def commit(failure_message: str) -> None:
    """Confirma a transação atual; em falha, desfaz e levanta o erro da aplicação."""
    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        # apenas o tipo do erro: a mensagem e o traceback carregam os dados que estavam sendo gravados
        logger.error('Falha ao gravar no banco (%s)', type(exc).__name__)
        raise PersistenceError(failure_message) from exc


class PersistableMixin:
    """Operações de escrita comuns às entidades, com as mensagens de erro da API."""

    CREATE_ERROR_MESSAGE = 'Erro ao criar registro'
    UPDATE_ERROR_MESSAGE = 'Erro ao atualizar'
    DELETE_ERROR_MESSAGE = 'Erro ao deletar'

    def assign(self, fields: dict) -> None:
        """Aplica os campos já validados à entidade."""
        for name, value in fields.items():
            setattr(self, name, value)

    def create(self) -> None:
        db.session.add(self)
        commit(self.CREATE_ERROR_MESSAGE)

    def update(self) -> None:
        commit(self.UPDATE_ERROR_MESSAGE)

    def delete(self) -> None:
        db.session.delete(self)
        commit(self.DELETE_ERROR_MESSAGE)
