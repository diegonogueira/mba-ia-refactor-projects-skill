"""Composition root: builds the Flask app and wires config, database, services, controllers and views."""
from flask import Flask
from flask_cors import CORS

from src.config.logging_config import configure_logging
from src.config.settings import Settings, load_settings
from src.controllers.category_controller import CategoryController
from src.controllers.health_controller import HealthController
from src.controllers.report_controller import ReportController
from src.controllers.task_controller import TaskController
from src.controllers.user_controller import UserController
from src.middlewares.error_handler import register_error_handlers
from src.models.database import init_database
from src.services.auth_service import AuthService
from src.services.report_service import ReportService
from src.views.category_routes import build_category_blueprint
from src.views.health_routes import build_health_blueprint
from src.views.report_routes import build_report_blueprint
from src.views.task_routes import build_task_blueprint
from src.views.user_routes import build_user_blueprint


def create_app(settings: Settings | None = None, overrides: dict | None = None) -> Flask:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    app = Flask(__name__)
    app.config.from_mapping({
        "SECRET_KEY": settings.secret_key,
        "SQLALCHEMY_DATABASE_URI": settings.database_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        **(overrides or {}),
    })
    CORS(app, origins=settings.cors_origins)
    init_database(app)

    report_service = ReportService()
    auth_service = AuthService(app.config["SECRET_KEY"])

    app.register_blueprint(build_health_blueprint(HealthController()))
    app.register_blueprint(build_task_blueprint(TaskController(report_service)))
    app.register_blueprint(build_user_blueprint(UserController(auth_service)))
    app.register_blueprint(build_category_blueprint(CategoryController()))
    app.register_blueprint(build_report_blueprint(ReportController(report_service)))
    register_error_handlers(app)
    return app
