"""Response representations. Every serializer lists its public fields explicitly (no password hashes)."""
from datetime import datetime


def _optional_datetime(value: datetime | None) -> str | None:
    return str(value) if value else None


# --- tasks

def serialize_task(task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "user_id": task.user_id,
        "category_id": task.category_id,
        "created_at": str(task.created_at),
        "updated_at": str(task.updated_at),
        "due_date": _optional_datetime(task.due_date),
        "tags": task.tag_list,
    }


def serialize_task_detail(task, now: datetime) -> dict:
    return {**serialize_task(task), "overdue": task.is_overdue(now)}


def serialize_task_listing(task, now: datetime) -> dict:
    return {
        **serialize_task_detail(task, now),
        "user_name": task.user.name if task.user else None,
        "category_name": task.category.name if task.category else None,
    }


def serialize_user_task(task, now: datetime) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "created_at": str(task.created_at),
        "due_date": _optional_datetime(task.due_date),
        "overdue": task.is_overdue(now),
    }


# --- users

def serialize_user(user) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": str(user.created_at),
    }


def serialize_user_listing(user, task_count: int) -> dict:
    return {**serialize_user(user), "task_count": task_count}


def serialize_user_detail(user, tasks) -> dict:
    return {**serialize_user(user), "tasks": [serialize_task(task) for task in tasks]}


def serialize_login(user, token: str) -> dict:
    return {"message": "Login realizado com sucesso", "user": serialize_user(user), "token": token}


def serialize_user_report(user, statistics: dict) -> dict:
    return {"user": {"id": user.id, "name": user.name, "email": user.email}, "statistics": statistics}


# --- categories

def serialize_category(category) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "color": category.color,
        "created_at": str(category.created_at),
    }


def serialize_category_listing(category, task_count: int) -> dict:
    return {**serialize_category(category), "task_count": task_count}
