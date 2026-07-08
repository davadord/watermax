"""
Pruebas unitarias del cambio de contraseña propia
(app/blueprints/auth.py::validar_cambio_password).

Ejercitan la función de validación directamente, sin HTTP/test client.
"""
from app.blueprints.auth import validar_cambio_password


def test_password_actual_incorrecta_no_actualiza(factory):
    user = factory.usuario(password="correcta123")

    error = validar_cambio_password(user, "incorrecta", "nuevaclave123", "nuevaclave123")

    assert error is not None
    assert "actual" in error.lower()


def test_password_nueva_menor_a_8_caracteres_no_actualiza(factory):
    user = factory.usuario(password="correcta123")

    error = validar_cambio_password(user, "correcta123", "corta", "corta")

    assert error is not None
    assert "8 caracteres" in error


def test_confirmacion_no_coincide_no_actualiza(factory):
    user = factory.usuario(password="correcta123")

    error = validar_cambio_password(user, "correcta123", "nuevaclave123", "otraclave123")

    assert error is not None
    assert "coincide" in error.lower()


def test_cambio_valido_no_devuelve_error(factory):
    user = factory.usuario(password="correcta123")

    error = validar_cambio_password(user, "correcta123", "nuevaclave123", "nuevaclave123")

    assert error is None


def test_cambio_valido_no_altera_el_hash_por_si_solo(factory):
    # validar_cambio_password solo valida; el hash lo aplica la vista tras
    # confirmar que error is None (RF-04, verificado en test_user.py).
    user = factory.usuario(password="correcta123")

    validar_cambio_password(user, "correcta123", "nuevaclave123", "nuevaclave123")

    assert user.check_password("correcta123")
