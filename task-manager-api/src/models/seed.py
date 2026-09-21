"""Dados iniciais do projeto, usados pelo script `seed.py` da raiz."""
import os
import secrets
from datetime import timedelta

from sqlalchemy import delete

from src.models.category_model import Category
from src.models.database import commit, db
from src.models.task_model import Task
from src.models.user_model import MIN_PASSWORD_LENGTH, User
from src.utils.datetime_utils import utcnow_naive

SEED_ERROR_MESSAGE = 'Erro ao popular o banco'

SEED_PASSWORD_VARIABLE = 'SEED_PASSWORD'
GENERATED_PASSWORD_BYTES = 12

# Os usuários de exemplo incluem papéis privilegiados; por isso a senha nunca fica fixa no código:
# vem de SEED_PASSWORD ou é sorteada a cada seed e mostrada uma única vez pelo script.
SEED_USERS = (
    {'name': 'João Silva', 'email': 'joao@email.com', 'role': 'admin'},
    {'name': 'Maria Santos', 'email': 'maria@email.com', 'role': 'user'},
    {'name': 'Pedro Oliveira', 'email': 'pedro@email.com', 'role': 'manager'},
)

SEED_CATEGORIES = (
    {'name': 'Backend', 'description': 'Tarefas de backend', 'color': '#3498db'},
    {'name': 'Frontend', 'description': 'Tarefas de frontend', 'color': '#2ecc71'},
    {'name': 'DevOps', 'description': 'Tarefas de infraestrutura', 'color': '#e74c3c'},
    {'name': 'Bug', 'description': 'Correção de bugs', 'color': '#e67e22'},
)

# `user` e `category` são índices nas tuplas acima; `due_in_days` é relativo ao momento do seed.
SEED_TASKS = (
    {'title': 'Implementar autenticação JWT', 'description': 'Adicionar autenticação real com JWT',
     'status': 'pending', 'priority': 1, 'user': 0, 'category': 0, 'due_in_days': -3},
    {'title': 'Criar tela de login', 'description': 'Tela de login responsiva',
     'status': 'in_progress', 'priority': 2, 'user': 1, 'category': 1, 'due_in_days': 5},
    {'title': 'Configurar CI/CD', 'description': 'Pipeline com GitHub Actions',
     'status': 'done', 'priority': 2, 'user': 2, 'category': 2, 'tags': 'devops,ci,github'},
    {'title': 'Corrigir bug no filtro de busca', 'description': 'Filtro não funciona com caracteres especiais',
     'status': 'pending', 'priority': 1, 'user': 0, 'category': 3, 'due_in_days': -1},
    {'title': 'Adicionar paginação na API', 'description': 'Endpoints retornam todos os registros',
     'status': 'pending', 'priority': 3, 'user': 0, 'category': 0, 'due_in_days': 10},
    {'title': 'Escrever testes unitários', 'description': 'Cobertura mínima de 80%',
     'status': 'pending', 'priority': 2, 'user': 1, 'category': 0},
    {'title': 'Documentar API com Swagger', 'description': 'Gerar documentação automática',
     'status': 'cancelled', 'priority': 4, 'user': 2, 'category': 0},
    {'title': 'Refatorar models', 'description': 'Melhorar organização dos models',
     'status': 'in_progress', 'priority': 3, 'user': 1, 'category': 0, 'tags': 'refactor,tech-debt'},
    {'title': 'Configurar monitoramento', 'description': 'Prometheus + Grafana',
     'status': 'pending', 'priority': 4, 'user': 2, 'category': 2, 'due_in_days': 20},
    {'title': 'Melhorar validações de input', 'description': 'Usar marshmallow ou pydantic',
     'status': 'pending', 'priority': 3, 'user': 0, 'category': 0, 'tags': 'improvement,validation'},
)


def seed_password() -> tuple[str, bool]:
    """Senha dos usuários de exemplo: a de `SEED_PASSWORD` ou uma sorteada agora.

    Devolve `(senha, foi_gerada)` — quando gerada, o script do seed a exibe uma única vez.
    """
    configured = os.environ.get(SEED_PASSWORD_VARIABLE)
    if not configured:
        return secrets.token_urlsafe(GENERATED_PASSWORD_BYTES), True
    if len(configured) < MIN_PASSWORD_LENGTH:
        raise ValueError(f'{SEED_PASSWORD_VARIABLE} deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres')
    return configured, False


def seed_database() -> dict:
    """Recria os dados de exemplo em uma única transação e devolve as contagens e a senha usada."""
    now = utcnow_naive()
    password, generated = seed_password()

    for entity in (Task, User, Category):
        db.session.execute(delete(entity))

    users = [User(**data) for data in SEED_USERS]
    for user in users:
        user.set_password(password)
    categories = [Category(**data) for data in SEED_CATEGORIES]
    db.session.add_all(users + categories)
    db.session.flush()

    for data in SEED_TASKS:
        task = Task(
            title=data['title'],
            description=data['description'],
            status=data['status'],
            priority=data['priority'],
            user_id=users[data['user']].id,
            category_id=categories[data['category']].id,
            tags=data.get('tags'),
        )
        if 'due_in_days' in data:
            task.due_date = now + timedelta(days=data['due_in_days'])
        db.session.add(task)

    commit(SEED_ERROR_MESSAGE)
    return {
        'users': User.count_all(),
        'categories': Category.count_all(),
        'tasks': Task.count_all(),
        'password': password,
        'password_generated': generated,
    }
