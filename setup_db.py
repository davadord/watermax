"""
Ejecutar una sola vez para crear las tablas e insertar datos iniciales.
Uso: python setup_db.py

IMPORTANTE: Después de ejecutar este script por primera vez, ejecuta:
    flask db stamp head
para que Alembic registre las migraciones como ya aplicadas.
"""
from sqlalchemy import select
from app import create_app, db
from app.models.user import Usuario
from app.models.client import Zona
from app.models.equipment import TipoEquipo, Componente, TipoEquipoComponente

app = create_app("development")

# (nombre, intervalo_nominal en meses)
COMPONENTES = [
    ("Filtro alcalino",            12),
    ("Filtro Cascara de coco T33",  8),
    ("Filtro de carbón activado",  12),
    ("Filtro de carbon de bloque", 12),
    ("Filtro de sedimento",         4),
    ("Lámpara UV 6w",              12),
    ("Membrana de ósmosis inversa", 24),
]

# (nombre, marca, [nombres de componentes incluidos])
TIPOS_EQUIPO = [
    ("OSMOSIS INVERSA 100 GPD UV", "Genérico", [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de carbon de bloque", "Filtro de sedimento",
        "Lámpara UV 6w", "Membrana de ósmosis inversa",
    ]),
    ("OSMOSIS INVERSA 100 GPD", None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de carbon de bloque", "Filtro de sedimento",
        "Membrana de ósmosis inversa",
    ]),
    ("PURIFICADOR W14 UV", None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de carbon de bloque", "Filtro de sedimento",
        "Lámpara UV 6w",
    ]),
    ("PURIFICADOR W14", None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de carbon de bloque", "Filtro de sedimento",
    ]),
    ("PURIFICADOR W13 UV", None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de sedimento", "Lámpara UV 6w",
    ]),
    ("BEBEDERO AGUA FRIA W13 UV", None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de sedimento", "Lámpara UV 6w",
    ]),
]


def _get_or_create_componente(nombre, intervalo):
    c = db.session.execute(
        select(Componente).where(Componente.nombre == nombre)
    ).scalars().first()
    if not c:
        c = Componente(nombre=nombre, intervalo_nominal=intervalo)
        db.session.add(c)
        db.session.flush()
        print(f"  + Componente: {nombre} ({intervalo} meses)")
    return c


def _get_or_create_tipo(nombre, marca, comps_map, comp_nombres):
    tipo = db.session.execute(
        select(TipoEquipo).where(TipoEquipo.nombre == nombre)
    ).scalars().first()
    if not tipo:
        tipo = TipoEquipo(nombre=nombre, marca=marca)
        db.session.add(tipo)
        db.session.flush()
        for cn in comp_nombres:
            db.session.add(TipoEquipoComponente(
                tipo_equipo_id=tipo.id,
                componente_id=comps_map[cn].id,
            ))
        print(f"  + Tipo: {nombre} ({len(comp_nombres)} componentes)")
    return tipo


with app.app_context():
    db.create_all()
    print("Tablas verificadas.")

    for email, nombre, rol in [
        ("admin@watermax.ec",   "Propietario Watermax",    "propietario"),
        ("admin2@watermax.ec",  "Administrativo Watermax", "administrativo"),
        ("tecnico@watermax.ec", "Técnico Watermax",        "tecnico"),
    ]:
        if not db.session.execute(select(Usuario).where(Usuario.email == email)).scalars().first():
            u = Usuario(nombre=nombre, email=email, rol=rol)
            u.set_password("Watermax2026!")
            db.session.add(u)
            print(f"  + Usuario: {email}")

    for nombre in ["Norte", "Centro-Norte", "Noroeste", "Centro", "Centro-Sur", "Sur"]:
        if not db.session.execute(select(Zona).where(Zona.nombre == nombre)).scalars().first():
            db.session.add(Zona(nombre=nombre))
            print(f"  + Zona: {nombre}")

    comps_map = {}
    for nombre, intervalo in COMPONENTES:
        comps_map[nombre] = _get_or_create_componente(nombre, intervalo)

    for nombre, marca, comp_nombres in TIPOS_EQUIPO:
        _get_or_create_tipo(nombre, marca, comps_map, comp_nombres)

    db.session.commit()
    print("\nDatos iniciales listos.")
    print("\nCredenciales:")
    print("  admin@watermax.ec     / Watermax2026!  (propietario)")
    print("  admin2@watermax.ec    / Watermax2026!  (administrativo)")
    print("  tecnico@watermax.ec   / Watermax2026!  (tecnico)")
    print("\n--- PASO SIGUIENTE ---")
    print("Ejecuta: flask db stamp head")
