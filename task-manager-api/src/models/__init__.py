"""Camada de modelos: entidades e acesso a dados.

Importar o pacote registra todas as entidades no metadata antes do `db.create_all()`.
"""
from src.models.category_model import Category
from src.models.task_model import Task
from src.models.user_model import User

__all__ = ('Category', 'Task', 'User')
