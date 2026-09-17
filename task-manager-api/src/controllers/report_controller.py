"""Controller de relatórios."""
from flask import jsonify

from src.views.serializers import serialize_summary_report, serialize_user_report


class ReportController:
    def __init__(self, report_service):
        self._reports = report_service

    def summary(self):
        return jsonify(serialize_summary_report(self._reports.summary())), 200

    def user_report(self, user_id):
        return jsonify(serialize_user_report(self._reports.user_report(user_id))), 200
