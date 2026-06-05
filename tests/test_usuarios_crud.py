"""
Pruebas del CRUD de gestión de usuarios (app/blueprints/admin.py).

Cubren dos capas:
  1. Lógica de validación pura (_validar_usuario): nombre, email, rol, password.
  2. Restricciones de acceso en las vistas: solo propietario gestiona usuarios
     y no puede desactivar su propia cuenta.

La autenticación se inyecta directamente en la sesión de Flask-Login
(session_transaction), sin pasar por la ruta /auth/login, siguiendo el
patrón ya establecido en test_decorators.py.
"""
from app.blueprints.admin import _validar_usuario
from app.models.user import Usuario


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


def _autenticar(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def _recargar(session, user_id):
    session.expire_all()
    return session.get(Usuario, user_id)


# ── C1: nombre obligatorio ─────────────────────────────────────────────────

def test_nombre_vacio_devuelve_error(app):
    error = _validar_usuario(_form(nombre=""), exclude_id=None, es_creacion=True)

    assert error is not None
    assert "nombre" in error.lower()


def test_nombre_solo_espacios_devuelve_error(app):
    error = _validar_usuario(_form(nombre="   "), exclude_id=None, es_creacion=True)

    assert error is not None


# ── C2: formato de email ───────────────────────────────────────────────────

def test_email_sin_arroba_devuelve_error(app):
    error = _validar_usuario(_form(email="sinArroba"), exclude_id=None, es_creacion=True)

    assert error is not None


def test_email_sin_punto_en_dominio_devuelve_error(app):
    error = _validar_usuario(_form(email="user@dominio"), exclude_id=None, es_creacion=True)

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

def test_propietario_no_puede_eliminarse_a_si_mismo(client, session, factory):
    propietario = factory.usuario(rol="propietario", email="jefe@test.com")
    _autenticar(client, propietario)

    resp = client.post(
        f"/admin/usuarios/{propietario.id}/eliminar",
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert _recargar(session, propietario.id).activo is True


def test_propietario_puede_desactivar_otro_usuario(client, session, factory):
    propietario = factory.usuario(rol="propietario", email="jefe@test.com")
    tecnico = factory.usuario(rol="tecnico", email="tec@test.com")
    _autenticar(client, propietario)

    resp = client.post(
        f"/admin/usuarios/{tecnico.id}/eliminar",
        follow_redirects=False,
    )

    assert resp.status_code == 302
    assert _recargar(session, tecnico.id).activo is False


# ── C7: control de acceso por rol ─────────────────────────────────────────

def test_administrativo_recibe_403_en_listar_usuarios(client, factory):
    admin = factory.usuario(rol="administrativo", email="admin@test.com")
    _autenticar(client, admin)

    resp = client.get("/admin/usuarios")

    assert resp.status_code == 403


def test_tecnico_recibe_403_en_listar_usuarios(client, factory):
    tecnico = factory.usuario(rol="tecnico", email="tec@test.com")
    _autenticar(client, tecnico)

    resp = client.get("/admin/usuarios")

    assert resp.status_code == 403


def test_propietario_accede_a_listar_usuarios(client, factory):
    propietario = factory.usuario(rol="propietario", email="jefe@test.com")
    _autenticar(client, propietario)

    resp = client.get("/admin/usuarios")

    assert resp.status_code == 200
