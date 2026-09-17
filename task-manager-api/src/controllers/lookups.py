"""Entity lookups shared by controllers: missing records become NotFoundError (404)."""
from src.models import Category, Task, User
from src.utils.errors import NotFoundError


def find_task_or_404(task_id: int) -> Task:
    task = Task.find_by_id(task_id)
    if task is None:
        raise NotFoundError("Task não encontrada")
    return task


def find_user_or_404(user_id: int) -> User:
    user = User.find_by_id(user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado")
    return user


def find_category_or_404(category_id: int) -> Category:
    category = Category.find_by_id(category_id)
    if category is None:
        raise NotFoundError("Categoria não encontrada")
    return category
