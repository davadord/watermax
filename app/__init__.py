from flask import Flask
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

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.controllers.auth import auth_bp
    from app.controllers.admin import admin_bp
    from app.controllers.maintenance import maintenance_bp
    from app.controllers.reports import reports_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(maintenance_bp, url_prefix="/maintenance")
    app.register_blueprint(reports_bp, url_prefix="/reports")

    from flask import redirect, url_for

    @app.route("/")
    def index():
        return redirect(url_for("reports.dashboard"))

    return app
