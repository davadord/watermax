from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import select

from app import db
from app.models.user import Usuario

auth_bp = Blueprint("auth", __name__)

LOGIN_OK = "ok"
LOGIN_CREDENCIALES_INVALIDAS = "credenciales_invalidas"
LOGIN_BLOQUEADO = "bloqueado"
LOGIN_CONTRASENA_INCORRECTA = "contrasena_incorrecta"

UMBRAL_INTENTOS_FALLIDOS = 5
DURACION_BLOQUEO = timedelta(minutes=15)


def intentar_login(user, password, ahora=None):
    """
    Lógica pura de autenticación: verifica bloqueo y contraseña, y actualiza
    el contador de intentos fallidos / bloqueo temporal sobre el objeto user
    (sin persistir ni tocar la sesión de Flask-Login).

    Retorna uno de los códigos LOGIN_*. El caller decide qué hacer con cada uno
    (flash, login_user, commit).
    """
    ahora = ahora or datetime.utcnow()

    if user is None:
        return LOGIN_CREDENCIALES_INVALIDAS

    if user.bloqueado_hasta and user.bloqueado_hasta > ahora:
        return LOGIN_BLOQUEADO

    if user.check_password(password):
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        return LOGIN_OK

    user.intentos_fallidos += 1
    if user.intentos_fallidos >= UMBRAL_INTENTOS_FALLIDOS:
        user.bloqueado_hasta = ahora + DURACION_BLOQUEO
    return LOGIN_CONTRASENA_INCORRECTA


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = db.session.execute(
            select(Usuario).where(Usuario.email == email, Usuario.activo == True)
        ).scalars().first()

        resultado = intentar_login(user, password)

        if resultado == LOGIN_CREDENCIALES_INVALIDAS:
            flash("Credenciales incorrectas.", "danger")
        elif resultado == LOGIN_BLOQUEADO:
            flash("Cuenta bloqueada temporalmente. Intenta en 15 minutos.", "danger")
        elif resultado == LOGIN_OK:
            db.session.commit()
            login_user(user)
            return redirect(url_for("reports.dashboard"))
        else:
            db.session.commit()
            if user.bloqueado_hasta:
                flash("Demasiados intentos. Cuenta bloqueada 15 minutos.", "danger")
            else:
                flash(f"Credenciales incorrectas. Intento {user.intentos_fallidos}/5.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


LONGITUD_MINIMA_PASSWORD = 8


def validar_cambio_password(user, password_actual, password_nueva, password_confirmar):
    """
    Lógica pura de validación del cambio de contraseña propia. Retorna un
    mensaje de error, o None si es válido. No aplica el cambio.
    """
    if not user.check_password(password_actual):
        return "La contraseña actual es incorrecta."
    if len(password_nueva) < LONGITUD_MINIMA_PASSWORD:
        return "La nueva contraseña debe tener al menos 8 caracteres."
    if password_nueva != password_confirmar:
        return "La confirmación no coincide con la nueva contraseña."
    return None


@auth_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        password_actual = request.form.get("password_actual", "")
        password_nueva = request.form.get("password_nueva", "")
        password_confirmar = request.form.get("password_confirmar", "")

        error = validar_cambio_password(
            current_user, password_actual, password_nueva, password_confirmar
        )
        if error:
            flash(error, "danger")
        else:
            current_user.set_password(password_nueva)
            db.session.commit()
            flash("Contraseña actualizada correctamente.", "success")
            return redirect(url_for("auth.perfil"))

    return render_template("auth/perfil.html")
