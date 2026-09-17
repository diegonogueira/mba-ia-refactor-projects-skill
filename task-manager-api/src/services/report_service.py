"""Relatórios e estatísticas: casos de uso que combinam tasks, usuários e categorias."""
from datetime import datetime, timedelta

from src.models.category_model import Category
from src.models.task_model import NO_TASKS, TASK_STATUSES, Task
from src.models.user_model import User
from src.utils.datetime_utils import utcnow_naive
from src.utils.errors import NotFoundError
from src.utils.math_utils import calculate_percentage

REPORT_WINDOW_DAYS = 7
USER_NOT_FOUND_MESSAGE = 'Usuário não encontrado'


class ReportService:
    def task_statistics(self, now: datetime | None = None) -> dict:
        """Números do endpoint /tasks/stats."""
        now = now or utcnow_naive()
        by_status = Task.count_by_status()
        total = Task.count_all()
        return {
            'total': total,
            'by_status': by_status,
            'overdue': Task.count_overdue(now),
            'completion_rate': calculate_percentage(by_status['done'], total),
        }

    def summary(self, now: datetime | None = None) -> dict:
        """Visão geral: totais, status, prioridades, atrasos, atividade recente e produtividade."""
        now = now or utcnow_naive()
        window_start = now - timedelta(days=REPORT_WINDOW_DAYS)
        overdue_tasks = Task.list_overdue(now)
        counts_by_user = Task.count_by_user()

        return {
            'generated_at': now,
            'total_tasks': Task.count_all(),
            'total_users': User.count_all(),
            'total_categories': Category.count_all(),
            'by_status': Task.count_by_status(),
            'by_priority': Task.count_by_priority(),
            'overdue_tasks': [(task, task.days_overdue(now)) for task in overdue_tasks],
            'created_in_window': Task.count_created_since(window_start),
            'completed_in_window': Task.count_completed_since(window_start),
            'user_productivity': [self._productivity(user, counts_by_user.get(user.id, NO_TASKS))
                                  for user in User.list_all()],
        }

    def user_report(self, user_id, now: datetime | None = None) -> dict:
        """Estatísticas das tasks de um usuário."""
        now = now or utcnow_naive()
        user = User.get_by_id(user_id)
        if user is None:
            raise NotFoundError(USER_NOT_FOUND_MESSAGE)

        tasks = Task.list_by_user(user_id)
        by_status = {status: 0 for status in TASK_STATUSES}
        for task in tasks:
            if task.status in by_status:
                by_status[task.status] += 1

        return {
            'user': user,
            'total': len(tasks),
            'by_status': by_status,
            'overdue': sum(1 for task in tasks if task.is_overdue(now)),
            'high_priority': sum(1 for task in tasks if task.is_high_priority()),
            'completion_rate': calculate_percentage(by_status['done'], len(tasks)),
        }

    @staticmethod
    def _productivity(user: User, counts) -> dict:
        return {
            'user': user,
            'total': counts.total,
            'completed': counts.completed,
            'completion_rate': calculate_percentage(counts.completed, counts.total),
        }
