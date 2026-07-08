"""
Fixtures compartidas de la suite de pruebas unitarias de Watermax.

Aísla la base de datos con SQLite en memoria (config "testing"). Cada prueba
recibe un esquema limpio: create_all() en el setup, drop_all() en el teardown,
de modo que ninguna prueba depende del estado dejada por otra.

Las factories crean objetos reales del ORM (no mocks) para que el motor
predictivo opere sobre relaciones SQLAlchemy auténticas.
"""
import pytest

from app import create_app, db

# Importa los modelos para que db.create_all() registre todas las tablas.
from app.models.user import Usuario
from app.models.client import Zona, Cliente
from app.models.equipment import (
    TipoEquipo,
    Componente,
    TipoEquipoComponente,
    EquipoInstalado,
)
from app.models.maintenance import Mantenimiento, DetalleMantenimiento


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def session(app):
    return db.session


class Factory:
    """Constructores mínimos de objetos ORM, encadenados sobre una sesión."""

    def __init__(self, session):
        self.session = session
        self._seq = 0

    def _next(self):
        self._seq += 1
        return self._seq

    def zona(self, nombre=None):
        z = Zona(nombre=nombre or f"Zona {self._next()}")
        self.session.add(z)
        self.session.commit()
        return z

    def cliente(self, nombre="Cliente Test"):
        c = Cliente(
            nombre=nombre,
            tipo_identificador="Cédula",
            identificador=f"ID{self._next():09d}",
        )
        self.session.add(c)
        self.session.commit()
        return c

    def componente(self, nombre=None, intervalo_nominal_meses=6):
        """intervalo_nominal_meses: el campo es en MESES (D2); el motor lo *30."""
        comp = Componente(
            nombre=nombre or f"Componente {self._next()}",
            intervalo_nominal=intervalo_nominal_meses,
        )
        self.session.add(comp)
        self.session.commit()
        return comp

    def tipo_equipo(self, nombre="Tipo Test", componentes=()):
        te = TipoEquipo(nombre=nombre)
        self.session.add(te)
        self.session.flush()
        for comp in componentes:
            self.session.add(
                TipoEquipoComponente(tipo_equipo_id=te.id, componente_id=comp.id)
            )
        self.session.commit()
        return te

    def equipo(self, tipo_equipo, fecha_instalacion, zona=None, cliente=None,
               fecha_reactivacion=None, activo=True):
        eq = EquipoInstalado(
            cliente_id=(cliente or self.cliente()).id,
            tipo_equipo_id=tipo_equipo.id,
            zona_id=(zona or self.zona()).id,
            fecha_instalacion=fecha_instalacion,
            fecha_reactivacion=fecha_reactivacion,
            activo=activo,
        )
        self.session.add(eq)
        self.session.commit()
        return eq

    def usuario(self, rol="tecnico", email=None, password="secreta123",
                nombre="Usuario Test", activo=True):
        u = Usuario(
            nombre=nombre,
            email=email or f"user{self._next()}@test.com",
            rol=rol,
            activo=activo,
            intentos_fallidos=0,
        )
        u.set_password(password)
        self.session.add(u)
        self.session.commit()
        return u

    def mantenimiento(self, equipo, fecha, detalles, tecnico=None,
                      completado=True, motivo_anulacion=None):
        """detalles: lista de (componente, accion) con accion en
        {"reemplazo", "limpieza", "revision"}."""
        tec = tecnico or self.usuario(rol="tecnico")
        m = Mantenimiento(
            equipo_id=equipo.id,
            tecnico_id=tec.id,
            fecha=fecha,
            completado=completado,
            motivo_anulacion=motivo_anulacion,
        )
        self.session.add(m)
        self.session.flush()
        for comp, accion in detalles:
            self.session.add(
                DetalleMantenimiento(
                    mantenimiento_id=m.id,
                    componente_id=comp.id,
                    accion=accion,
                )
            )
        self.session.commit()
        return m


@pytest.fixture
def factory(session):
    return Factory(session)
