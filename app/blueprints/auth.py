from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from datetime import datetime, timedelta
from sqlalchemy import select

from app import db
from app.models.user import Usuario

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = db.session.execute(
            select(Usuario).where(Usuario.email == email, Usuario.activo == True)
        ).scalars().first()

        if user is None:
            flash("Credenciales incorrectas.", "danger")
            return render_template("auth/login.html")

        # Verificar bloqueo temporal
        if user.bloqueado_hasta and user.bloqueado_hasta > datetime.utcnow():
            flash("Cuenta bloqueada temporalmente. Intenta en 15 minutos.", "danger")
            return render_template("auth/login.html")

        if user.check_password(password):
            user.intentos_fallidos = 0
            user.bloqueado_hasta = None
            db.session.commit()
            login_user(user)
            return redirect(url_for("reports.dashboard"))
        else:
            user.intentos_fallidos += 1
            if user.intentos_fallidos >= 5:
                user.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=15)
                flash("Demasiados intentos. Cuenta bloqueada 15 minutos.", "danger")
            else:
                flash(f"Credenciales incorrectas. Intento {user.intentos_fallidos}/5.", "danger")
            db.session.commit()

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
