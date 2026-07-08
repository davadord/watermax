"""
Pruebas unitarias del CRUD de gestión de usuarios (app/blueprints/admin.py).

Cubren dos capas, ambas mediante llamadas directas a funciones puras, sin
HTTP/test client:
  1. Validación de formulario (_validar_usuario): nombre, email, rol, password.
  2. Regla de negocio (puede_desactivar_usuario): nadie se desactiva a sí mismo.
"""
import pytest

from app.blueprints.admin import _validar_usuario, puede_desactivar_usuario, _solo_propietario


def _form(**kwargs):
    """Dict de formulario con valores por defecto válidos para una creación."""
    base = {
        "nombre": "Nuevo Usuario",
        "email": "nuevo@test.com",
        "rol": "tecnico",
        "password": "clave123",
        "confirmar": "clave123",
    }
    base.update(kwargs)
    return base


# ── C1: nombre obligatorio ─────────────────────────────────────────────────

@pytest.mark.parametrize("nombre_invalido", ["", "   "])
def test_nombre_vacio_o_solo_espacios_devuelve_error(app, nombre_invalido):
    error = _validar_usuario(_form(nombre=nombre_invalido), exclude_id=None, es_creacion=True)

    assert error is not None


# ── C2: formato de email ───────────────────────────────────────────────────

@pytest.mark.parametrize("email_invalido", ["sinArroba", "user@dominio"])
def test_email_con_formato_invalido_devuelve_error(app, email_invalido):
    error = _validar_usuario(_form(email=email_invalido), exclude_id=None, es_creacion=True)

    assert error is not None


def test_email_valido_no_devuelve_error_de_formato(app):
    error = _validar_usuario(_form(email="user@dominio.com"), exclude_id=None, es_creacion=True)

    assert error is None


# ── C3: unicidad de email en BD ────────────────────────────────────────────

def test_email_duplicado_en_creacion_devuelve_error(app, factory):
    factory.usuario(email="ocupado@test.com")

    error = _validar_usuario(_form(email="ocupado@test.com"), exclude_id=None, es_creacion=True)

    assert error is not None
    assert "ocupado@test.com" in error


def test_email_duplicado_excluye_propio_id_en_edicion(app, factory):
    usuario = factory.usuario(email="propio@test.com")

    error = _validar_usuario(
        _form(email="propio@test.com"),
        exclude_id=usuario.id,
        es_creacion=False,
    )

    assert error is None


def test_email_de_otro_usuario_en_edicion_devuelve_error(app, factory):
    factory.usuario(email="ocupado@test.com")
    editor = factory.usuario(email="editor@test.com")

    error = _validar_usuario(
        _form(email="ocupado@test.com"),
        exclude_id=editor.id,
        es_creacion=False,
    )

    assert error is not None


# ── C4: password obligatoria en creación, opcional en edición ─────────────

def test_password_vacia_en_creacion_devuelve_error(app):
    error = _validar_usuario(_form(password="", confirmar=""), exclude_id=None, es_creacion=True)

    assert error is not None
    assert "contraseña" in error.lower()


def test_password_vacia_en_edicion_no_devuelve_error(app):
    error = _validar_usuario(
        _form(email="nuevo@test.com", password="", confirmar=""),
        exclude_id=None,
        es_creacion=False,
    )

    assert error is None


# ── C5: passwords coincidentes ─────────────────────────────────────────────

def test_passwords_distintas_devuelven_error(app):
    error = _validar_usuario(
        _form(password="abc123", confirmar="xyz789"),
        exclude_id=None,
        es_creacion=True,
    )

    assert error is not None
    assert "coincid" in error.lower()


def test_passwords_iguales_no_devuelven_error(app):
    error = _validar_usuario(
        _form(password="segura123", confirmar="segura123"),
        exclude_id=None,
        es_creacion=True,
    )

    assert error is None


# ── C6: propietario no puede desactivarse a sí mismo ──────────────────────

def test_propietario_no_puede_eliminarse_a_si_mismo(factory):
    propietario = factory.usuario(rol="propietario", email="jefe@test.com")

    assert puede_desactivar_usuario(propietario, solicitante=propietario) is False


def test_propietario_puede_desactivar_otro_usuario(factory):
    propietario = factory.usuario(rol="propietario", email="jefe@test.com")
    tecnico = factory.usuario(rol="tecnico", email="tec@test.com")

    assert puede_desactivar_usuario(tecnico, solicitante=propietario) is True


# ── C7: solo propietario gestiona usuarios ─────────────────────────────────
# El control de acceso en sí (rol no permitido -> 403) ya se prueba
# unitariamente en test_decorators.py contra el decorador role_required.
# Aquí solo se verifica que las rutas de usuarios están restringidas al rol
# correcto, sin duplicar la prueba del decorador vía HTTP.

def test_gestion_de_usuarios_esta_restringida_a_propietario():
    assert _solo_propietario == ("propietario",)
