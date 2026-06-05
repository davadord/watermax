"""
Pruebas de caracterización del decorador @role_required
(app/utils/decorators.py).

Se montan dos vistas de prueba en la app "testing" (ver conftest.py):
- /_test/solo-admin   -> @role_required("propietario", "administrativo")
- /_test/solo-tecnico -> @role_required("tecnico")

Ambas llevan @login_required ENCIMA de @role_required, el orden documentado
en AGENTS.md. La autenticación se simula fijando la sesión de Flask-Login.
"""


def _autenticar(client, user):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user.id)
        sess["_fresh"] = True


def test_rol_propietario_accede_a_vista_de_admin(client, factory):
    user = factory.usuario(rol="propietario")
    _autenticar(client, user)

    resp = client.get("/_test/solo-admin")

    assert resp.status_code == 200
    assert resp.data == b"ok-admin"


def test_rol_administrativo_accede_a_vista_de_admin(client, factory):
    user = factory.usuario(rol="administrativo")
    _autenticar(client, user)

    resp = client.get("/_test/solo-admin")

    assert resp.status_code == 200


def test_rol_no_permitido_recibe_403(client, factory):
    user = factory.usuario(rol="tecnico")
    _autenticar(client, user)

    resp = client.get("/_test/solo-admin")

    assert resp.status_code == 403


def test_rol_tecnico_accede_a_su_vista(client, factory):
    user = factory.usuario(rol="tecnico")
    _autenticar(client, user)

    resp = client.get("/_test/solo-tecnico")

    assert resp.status_code == 200
    assert resp.data == b"ok-tecnico"


def test_propietario_no_accede_a_vista_exclusiva_de_tecnico(client, factory):
    user = factory.usuario(rol="propietario")
    _autenticar(client, user)

    resp = client.get("/_test/solo-tecnico")

    assert resp.status_code == 403


def test_usuario_no_autenticado_es_redirigido_por_login_required_antes_de_role(client):
    # Sin autenticar: si @role_required corriera primero, fallaría al leer
    # current_user.rol (AnonymousUser no tiene rol). El 302 a login prueba que
    # @login_required se evalúa antes.
    resp = client.get("/_test/solo-admin")

    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
