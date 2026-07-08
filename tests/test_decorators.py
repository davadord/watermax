"""
Pruebas unitarias del decorador @role_required (app/utils/decorators.py).

Se envuelve una función Python simple con el decorador real y se invoca
directamente dentro de un app_context, sustituyendo current_user por un stub
con el atributo .rol. Sin rutas HTTP ni test client.
"""
import pytest
from unittest.mock import patch

from app.utils.decorators import role_required


class _UsuarioStub:
    def __init__(self, rol):
        self.rol = rol


@pytest.fixture
def vista_solo_admin():
    @role_required("propietario", "administrativo")
    def vista():
        return "ok-admin"
    return vista


@pytest.fixture
def vista_solo_tecnico():
    @role_required("tecnico")
    def vista():
        return "ok-tecnico"
    return vista


def _con_usuario(rol, func, app):
    # test_request_context (no solo app_context) es necesario porque la vista
    # 403 real renderiza errors/403.html, y el context_processor global de la
    # app (app/__init__.py) lee flask_login.current_user para la navbar. El
    # patch cubre la verificación de rol en el decorador; el contexto de
    # request cubre ese acceso incidental de la plantilla.
    with app.test_request_context("/"), patch("app.utils.decorators.current_user", _UsuarioStub(rol)):
        return func()


def test_rol_propietario_accede_a_vista_de_admin(app, vista_solo_admin):
    resultado = _con_usuario("propietario", vista_solo_admin, app)

    assert resultado == "ok-admin"


def test_rol_administrativo_accede_a_vista_de_admin(app, vista_solo_admin):
    resultado = _con_usuario("administrativo", vista_solo_admin, app)

    assert resultado == "ok-admin"


def test_rol_no_permitido_recibe_403(app, vista_solo_admin):
    _, status = _con_usuario("tecnico", vista_solo_admin, app)

    assert status == 403


def test_rol_tecnico_accede_a_su_vista(app, vista_solo_tecnico):
    resultado = _con_usuario("tecnico", vista_solo_tecnico, app)

    assert resultado == "ok-tecnico"


def test_propietario_no_accede_a_vista_exclusiva_de_tecnico(app, vista_solo_tecnico):
    _, status = _con_usuario("propietario", vista_solo_tecnico, app)

    assert status == 403
