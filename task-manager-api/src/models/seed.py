"""Sample data for local development (users, categories and tasks)."""
from datetime import timedelta

from src.models.category_model import Category
from src.models.database import commit, db
from src.models.task_model import Task
from src.models.user_model import User
from src.utils.dates import utc_now

SEED_USERS = (
    {"name": "João Silva", "email": "joao@email.com", "password": "1234", "role": "admin"},
    {"name": "Maria Santos", "email": "maria@email.com", "password": "abcd", "role": "user"},
    {"name": "Pedro Oliveira", "email": "pedro@email.com", "password": "pass", "role": "manager"},
)

SEED_CATEGORIES = (
    {"name": "Backend", "description": "Tarefas de backend", "color": "#3498db"},
    {"name": "Frontend", "description": "Tarefas de frontend", "color": "#2ecc71"},
    {"name": "DevOps", "description": "Tarefas de infraestrutura", "color": "#e74c3c"},
    {"name": "Bug", "description": "Correção de bugs", "color": "#e67e22"},
)

# (title, description, status, priority, user email, category name, due in N days or None, tags)
SEED_TASKS = (
    ("Implementar autenticação JWT", "Adicionar autenticação real com JWT", "pending", 1,
     "joao@email.com", "Backend", -3, None),
    ("Criar tela de login", "Tela de login responsiva", "in_progress", 2,
     "maria@email.com", "Frontend", 5, None),
    ("Configurar CI/CD", "Pipeline com GitHub Actions", "done", 2,
     "pedro@email.com", "DevOps", None, "devops,ci,github"),
    ("Corrigir bug no filtro de busca", "Filtro não funciona com caracteres especiais", "pending", 1,
     "joao@email.com", "Bug", -1, None),
    ("Adicionar paginação na API", "Endpoints retornam todos os registros", "pending", 3,
     "joao@email.com", "Backend", 10, None),
    ("Escrever testes unitários", "Cobertura mínima de 80%", "pending", 2,
     "maria@email.com", "Backend", None, None),
    ("Documentar API com Swagger", "Gerar documentação automática", "cancelled", 4,
     "pedro@email.com", "Backend", None, None),
    ("Refatorar models", "Melhorar organização dos models", "in_progress", 3,
     "maria@email.com", "Backend", None, "refactor,tech-debt"),
    ("Configurar monitoramento", "Prometheus + Grafana", "pending", 4,
     "pedro@email.com", "DevOps", 20, None),
    ("Melhorar validações de input", "Usar marshmallow ou pydantic", "pending", 3,
     "joao@email.com", "Backend", None, "improvement,validation"),
)


def seed_database() -> dict[str, int]:
    """Replace all rows with the sample data in a single transaction and return the resulting counts."""
    for model in (Task, User, Category):
        db.session.execute(db.delete(model))

    users = {}
    for data in SEED_USERS:
        user = User(name=data["name"], email=data["email"], role=data["role"])
        user.set_password(data["password"])
        users[user.email] = user
    categories = {data["name"]: Category(**data) for data in SEED_CATEGORIES}
    db.session.add_all([*users.values(), *categories.values()])
    db.session.flush()  # assigns ids used by the tasks below

    now = utc_now()
    for title, description, status, priority, email, category_name, due_in_days, tags in SEED_TASKS:
        db.session.add(Task(
            title=title,
            description=description,
            status=status,
            priority=priority,
            user_id=users[email].id,
            category_id=categories[category_name].id,
            due_date=now + timedelta(days=due_in_days) if due_in_days is not None else None,
            tags=tags,
        ))

    commit("Erro ao popular o banco de dados")
    return {"users": User.count(), "categories": Category.count(), "tasks": Task.count()}
