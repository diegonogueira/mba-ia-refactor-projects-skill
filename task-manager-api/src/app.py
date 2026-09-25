"""Composition root: cria a aplicação e liga config, banco, services, controllers e views."""
import logging

from flask import Flask
from flask_cors import CORS

import src.models  # noqa: F401  — registra as entidades no metadata antes do db.create_all()
from src.config.settings import Settings, load_settings
from src.controllers.category_controller import CategoryController
from src.controllers.health_controller import HealthController
from src.controllers.report_controller import ReportController
from src.controllers.task_controller import TaskController
from src.controllers.user_controller import UserController
from src.middlewares.auth_guard import AuthGuard
from src.middlewares.error_handler import register_error_handlers
from src.models.database import ENGINE_OPTIONS, init_database
from src.services.auth_service import AuthService
from src.services.report_service import ReportService
from src.views.category_routes import build_category_blueprint
from src.views.health_routes import build_health_blueprint
from src.views.report_routes import build_report_blueprint
from src.views.task_routes import build_task_blueprint
from src.views.user_routes import build_user_blueprint

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or load_settings()
    logging.basicConfig(level=settings.log_level, format=LOG_FORMAT)

    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=settings.secret_key,
        SQLALCHEMY_DATABASE_URI=settings.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS=ENGINE_OPTIONS,
        ADMIN_TOKEN=settings.admin_token,
        ADMIN_ENDPOINTS_ENABLED=settings.admin_endpoints_enabled,
    )

    CORS(app, origins=settings.cors_origins)
    init_database(app)

    auth_service = AuthService(app.config['SECRET_KEY'], settings.token_max_age)
    auth_guard = AuthGuard(auth_service)
    report_service = ReportService()

    app.register_blueprint(build_health_blueprint(HealthController()))
    app.register_blueprint(build_task_blueprint(TaskController(report_service), auth_guard))
    app.register_blueprint(build_user_blueprint(UserController(auth_service), auth_guard))
    app.register_blueprint(build_category_blueprint(CategoryController(), auth_guard))
    app.register_blueprint(build_report_blueprint(ReportController(report_service), auth_guard))

    register_error_handlers(app)
    return app
