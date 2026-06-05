"""
Pruebas de caracterización del modelo Usuario (app/models/user.py).

Cubren el hashing de contraseñas con bcrypt: set_password() / check_password().

NOTA DE HALLAZGO: el modelo Usuario NO contiene la lógica de bloqueo por
intentos fallidos. Solo declara las columnas `intentos_fallidos` y
`bloqueado_hasta`. La lógica que las incrementa y fija el bloqueo vive en la
ruta de login (app/blueprints/auth.py). Por eso esas pruebas están en
test_auth_lockout.py, ejercitando el comportamiento donde realmente reside.
"""


def test_set_password_no_guarda_la_contrasena_en_claro(factory):
    user = factory.usuario(password="MiClaveSecreta123")

    assert user.password_hash is not None
    assert user.password_hash != "MiClaveSecreta123"
    assert "MiClaveSecreta123" not in user.password_hash


def test_check_password_devuelve_true_con_la_contrasena_correcta(factory):
    user = factory.usuario(password="claveCorrecta")

    assert user.check_password("claveCorrecta") is True


def test_check_password_devuelve_false_con_la_contrasena_incorrecta(factory):
    user = factory.usuario(password="claveCorrecta")

    assert user.check_password("claveIncorrecta") is False


def test_set_password_genera_un_hash_bcrypt_con_salt(factory):
    user = factory.usuario(password="misma")
    primer_hash = user.password_hash

    user.set_password("misma")

    # bcrypt usa salt aleatorio: el mismo texto produce hashes distintos,
    # y ambos verifican correctamente.
    assert user.password_hash != primer_hash
    assert user.check_password("misma") is True
