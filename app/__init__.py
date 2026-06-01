from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from config import config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

login_manager.login_view = "auth.login"
login_manager.login_message = "Inicia sesión para acceder a esta página."
login_manager.login_message_category = "warning"


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if config_name == "production":
        missing = [v for v in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI") if not app.config.get(v)]
        if missing:
            raise RuntimeError(
                f"Variables de entorno no configuradas: {', '.join(missing)}. "
                "Defínelas antes de iniciar la aplicación."
            )

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.blueprints.auth import auth_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.maintenance import maintenance_bp
    from app.blueprints.reports import reports_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(maintenance_bp, url_prefix="/maintenance")
    app.register_blueprint(reports_bp, url_prefix="/reports")

    from flask import redirect, url_for
    from flask_login import current_user

    @app.route("/")
    def index():
        return redirect(url_for("reports.dashboard"))

    NAVBAR_REPORTS_ENDPOINTS = {"reports.dashboard", "reports.criticos"}

    @app.context_processor
    def inject_globals():
        from flask import request as _req
        from app.services.prediction_service import get_equipos_criticos, URGENCIA_VENCIDO
        is_admin = (
            current_user.is_authenticated
            and getattr(current_user, "rol", None) in ("propietario", "administrativo")
        )
        alertas_count = 0
        if current_user.is_authenticated and _req.endpoint in NAVBAR_REPORTS_ENDPOINTS:
            criticos = get_equipos_criticos()
            alertas_count = sum(
                1 for item in criticos if item["urgencia_maxima"] == URGENCIA_VENCIDO
            )
        return {"is_admin": is_admin, "alertas_count": alertas_count}

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
