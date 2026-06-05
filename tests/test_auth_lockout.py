"""
Pruebas de caracterización del bloqueo por intentos fallidos.

La lógica vive en la ruta de login (app/blueprints/auth.py), no en el modelo
Usuario. Se ejercita a través del test client de Flask. Valores reales del
código: umbral = 5 intentos, duración = 15 minutos, marca de tiempo con
datetime.utcnow().
"""
from datetime import datetime, timedelta

from app.models.user import Usuario


def _login(client, email, password):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def _recargar(session, user_id):
    session.expire_all()
    return session.get(Usuario, user_id)


def test_login_fallido_incrementa_intentos(client, session, factory):
    user = factory.usuario(email="a@test.com", password="correcta")

    _login(client, "a@test.com", "incorrecta")

    user = _recargar(session, user.id)
    assert user.intentos_fallidos == 1
    assert user.bloqueado_hasta is None


def test_cuatro_intentos_fallidos_no_bloquean_la_cuenta(client, session, factory):
    user = factory.usuario(email="b@test.com", password="correcta")

    for _ in range(4):
        _login(client, "b@test.com", "mala")

    user = _recargar(session, user.id)
    assert user.intentos_fallidos == 4
    assert user.bloqueado_hasta is None


def test_quinto_intento_fallido_bloquea_la_cuenta_15_min(client, session, factory):
    user = factory.usuario(email="c@test.com", password="correcta")

    antes = datetime.utcnow()
    for _ in range(5):
        _login(client, "c@test.com", "mala")
    despues = datetime.utcnow()

    user = _recargar(session, user.id)
    assert user.intentos_fallidos == 5
    assert user.bloqueado_hasta is not None
    # El bloqueo apunta ~15 minutos al futuro respecto del momento del 5º intento.
    assert antes + timedelta(minutes=15) <= user.bloqueado_hasta <= despues + timedelta(minutes=15)


def test_cuenta_bloqueada_rechaza_incluso_la_contrasena_correcta(client, session, factory):
    user = factory.usuario(email="d@test.com", password="correcta")
    user.bloqueado_hasta = datetime.utcnow() + timedelta(minutes=15)
    session.commit()

    resp = _login(client, "d@test.com", "correcta")

    # El chequeo de bloqueo ocurre antes del de contraseña: no hay login (no 302).
    assert resp.status_code == 200
    user = _recargar(session, user.id)
    assert user.bloqueado_hasta is not None


def test_login_exitoso_reinicia_contador_y_desbloquea(client, session, factory):
    user = factory.usuario(email="e@test.com", password="correcta")
    user.intentos_fallidos = 3
    session.commit()

    resp = _login(client, "e@test.com", "correcta")

    assert resp.status_code == 302  # redirige al dashboard
    user = _recargar(session, user.id)
    assert user.intentos_fallidos == 0
    assert user.bloqueado_hasta is None
