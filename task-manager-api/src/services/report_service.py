"""Reporting use cases that aggregate tasks, users and categories."""
from datetime import datetime, timedelta

from src.models import Category, Task, User
from src.models.task_model import DONE_STATUS, PRIORITY_LABELS, VALID_STATUSES
from src.utils.calculations import calculate_percentage
from src.utils.dates import utc_now

RECENT_ACTIVITY_DAYS = 7


class ReportService:
    def task_statistics(self, now: datetime | None = None) -> dict:
        now = now or utc_now()
        total = Task.count()
        by_status = Task.count_by_status()
        return {
            "total": total,
            **self._status_counts(by_status),
            "overdue": Task.count_overdue(now),
            "completion_rate": calculate_percentage(by_status.get(DONE_STATUS, 0), total),
        }

    def summary(self, now: datetime | None = None) -> dict:
        now = now or utc_now()
        recent_since = now - timedelta(days=RECENT_ACTIVITY_DAYS)
        by_priority = Task.count_by_priority()
        overdue_tasks = Task.list_overdue(now)
        counts_by_user = Task.count_by_user()

        return {
            "generated_at": str(now),
            "overview": {
                "total_tasks": Task.count(),
                "total_users": User.count(),
                "total_categories": Category.count(),
            },
            "tasks_by_status": self._status_counts(Task.count_by_status()),
            "tasks_by_priority": {label: by_priority.get(priority, 0) for priority, label in PRIORITY_LABELS.items()},
            "overdue": {
                "count": len(overdue_tasks),
                "tasks": [
                    {
                        "id": task.id,
                        "title": task.title,
                        "due_date": str(task.due_date),
                        "days_overdue": (now - task.due_date).days,
                    }
                    for task in overdue_tasks
                ],
            },
            "recent_activity": {
                "tasks_created_last_7_days": Task.count_created_since(recent_since),
                "tasks_completed_last_7_days": Task.count_completed_since(recent_since),
            },
            "user_productivity": [
                self._user_productivity(user, *counts_by_user.get(user.id, (0, 0))) for user in User.list_all()
            ],
        }

    def user_statistics(self, user: User, now: datetime | None = None) -> dict:
        now = now or utc_now()
        total = Task.count(user_id=user.id)
        by_status = self._status_counts(Task.count_by_status(user_id=user.id))
        return {
            "total_tasks": total,
            "done": by_status["done"],
            "pending": by_status["pending"],
            "in_progress": by_status["in_progress"],
            "cancelled": by_status["cancelled"],
            "overdue": Task.count_overdue(now, user_id=user.id),
            "high_priority": Task.count_high_priority(user.id),
            "completion_rate": calculate_percentage(by_status["done"], total),
        }

    @staticmethod
    def _status_counts(by_status: dict[str, int]) -> dict[str, int]:
        return {status: by_status.get(status, 0) for status in VALID_STATUSES}

    @staticmethod
    def _user_productivity(user: User, total: int, completed: int) -> dict:
        return {
            "user_id": user.id,
            "user_name": user.name,
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": calculate_percentage(completed, total),
        }
