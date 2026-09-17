"""Serializers: convertem entidades e relatórios nos objetos JSON públicos da API."""
from datetime import datetime

LOGIN_SUCCESS_MESSAGE = 'Login realizado com sucesso'
PRIORITY_LABELS = {1: 'critical', 2: 'high', 3: 'medium', 4: 'low', 5: 'minimal'}


def _datetime(value: datetime | None) -> str:
    return str(value)


def _optional_datetime(value: datetime | None) -> str | None:
    return str(value) if value else None


# --- tasks -----------------------------------------------------------------

def serialize_task(task) -> dict:
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'user_id': task.user_id,
        'category_id': task.category_id,
        'created_at': _datetime(task.created_at),
        'updated_at': _datetime(task.updated_at),
        'due_date': _optional_datetime(task.due_date),
        'tags': task.tag_list,
    }


def serialize_task_detail(task, now: datetime | None = None) -> dict:
    return {**serialize_task(task), 'overdue': task.is_overdue(now)}


def serialize_task_with_relations(task, now: datetime | None = None) -> dict:
    return {
        **serialize_task_detail(task, now),
        'user_name': task.user.name if task.user else None,
        'category_name': task.category.name if task.category else None,
    }


def serialize_user_task(task, now: datetime | None = None) -> dict:
    """Formato reduzido usado em /users/<id>/tasks."""
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'created_at': _datetime(task.created_at),
        'due_date': _optional_datetime(task.due_date),
        'overdue': task.is_overdue(now),
    }


def serialize_task_statistics(statistics: dict) -> dict:
    return {
        'total': statistics['total'],
        **statistics['by_status'],
        'overdue': statistics['overdue'],
        'completion_rate': statistics['completion_rate'],
    }


# --- usuários --------------------------------------------------------------

def serialize_user(user) -> dict:
    """Campos públicos do usuário — o hash de senha nunca é exposto."""
    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'active': user.active,
        'created_at': _datetime(user.created_at),
    }


def serialize_user_with_task_count(user, task_count: int) -> dict:
    return {**serialize_user(user), 'task_count': task_count}


def serialize_user_with_tasks(user, tasks) -> dict:
    return {**serialize_user(user), 'tasks': [serialize_task(task) for task in tasks]}


def serialize_login(user, token: str) -> dict:
    return {'message': LOGIN_SUCCESS_MESSAGE, 'user': serialize_user(user), 'token': token}


# --- categorias ------------------------------------------------------------

def serialize_category(category, task_count: int | None = None) -> dict:
    data = {
        'id': category.id,
        'name': category.name,
        'description': category.description,
        'color': category.color,
        'created_at': _datetime(category.created_at),
    }
    if task_count is not None:
        data['task_count'] = task_count
    return data


# --- relatórios ------------------------------------------------------------

def serialize_summary_report(summary: dict) -> dict:
    return {
        'generated_at': _datetime(summary['generated_at']),
        'overview': {
            'total_tasks': summary['total_tasks'],
            'total_users': summary['total_users'],
            'total_categories': summary['total_categories'],
        },
        'tasks_by_status': dict(summary['by_status']),
        'tasks_by_priority': {PRIORITY_LABELS[priority]: count
                              for priority, count in summary['by_priority'].items()},
        'overdue': {
            'count': len(summary['overdue_tasks']),
            'tasks': [{'id': task.id, 'title': task.title, 'due_date': _datetime(task.due_date),
                       'days_overdue': days} for task, days in summary['overdue_tasks']],
        },
        'recent_activity': {
            'tasks_created_last_7_days': summary['created_in_window'],
            'tasks_completed_last_7_days': summary['completed_in_window'],
        },
        'user_productivity': [{'user_id': entry['user'].id,
                               'user_name': entry['user'].name,
                               'total_tasks': entry['total'],
                               'completed_tasks': entry['completed'],
                               'completion_rate': entry['completion_rate']}
                              for entry in summary['user_productivity']],
    }


def serialize_user_report(report: dict) -> dict:
    user = report['user']
    return {
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
        'statistics': {
            'total_tasks': report['total'],
            **report['by_status'],
            'overdue': report['overdue'],
            'high_priority': report['high_priority'],
            'completion_rate': report['completion_rate'],
        },
    }
