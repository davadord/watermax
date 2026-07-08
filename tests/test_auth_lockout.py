"""
Pruebas unitarias del bloqueo por intentos fallidos (app/blueprints/auth.py).

Ejercitan intentar_login() directamente, sin pasar por HTTP/test client.
Valores reales del código: umbral = 5 intentos, duración = 15 minutos.
"""
from datetime import datetime, timedelta

import pytest

from app.blueprints.auth import (
    intentar_login,
    LOGIN_OK,
    LOGIN_CREDENCIALES_INVALIDAS,
    LOGIN_BLOQUEADO,
    LOGIN_CONTRASENA_INCORRECTA,
)


def test_usuario_inexistente_devuelve_credenciales_invalidas():
    resultado = intentar_login(None, "cualquiera")

    assert resultado == LOGIN_CREDENCIALES_INVALIDAS


@pytest.mark.parametrize("n_intentos", [1, 4])
def test_intentos_fallidos_por_debajo_del_umbral_no_bloquean(factory, n_intentos):
    user = factory.usuario(password="correcta")

    for _ in range(n_intentos):
        resultado = intentar_login(user, "mala")

    assert resultado == LOGIN_CONTRASENA_INCORRECTA
    assert user.intentos_fallidos == n_intentos
    assert user.bloqueado_hasta is None


def test_quinto_intento_fallido_bloquea_la_cuenta_15_min(factory):
    user = factory.usuario(password="correcta")
    ahora = datetime(2026, 1, 1, 12, 0, 0)

    for _ in range(5):
        resultado = intentar_login(user, "mala", ahora=ahora)

    assert resultado == LOGIN_CONTRASENA_INCORRECTA
    assert user.intentos_fallidos == 5
    assert user.bloqueado_hasta == ahora + timedelta(minutes=15)


def test_cuenta_bloqueada_rechaza_incluso_la_contrasena_correcta(factory):
    user = factory.usuario(password="correcta")
    ahora = datetime(2026, 1, 1, 12, 0, 0)
    user.bloqueado_hasta = ahora + timedelta(minutes=15)

    resultado = intentar_login(user, "correcta", ahora=ahora)

    assert resultado == LOGIN_BLOQUEADO
    assert user.intentos_fallidos == 0  # no se toca mientras está bloqueada


def test_bloqueo_expira_tras_los_15_minutos(factory):
    user = factory.usuario(password="correcta")
    bloqueo_fijado = datetime(2026, 1, 1, 12, 0, 0)
    user.bloqueado_hasta = bloqueo_fijado

    resultado = intentar_login(user, "correcta", ahora=bloqueo_fijado + timedelta(minutes=15, seconds=1))

    assert resultado == LOGIN_OK


def test_login_exitoso_reinicia_contador_y_desbloquea(factory):
    user = factory.usuario(password="correcta")
    user.intentos_fallidos = 3

    resultado = intentar_login(user, "correcta")

    assert resultado == LOGIN_OK
    assert user.intentos_fallidos == 0
    assert user.bloqueado_hasta is None
