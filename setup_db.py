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
from app.models.client import Zona, Cliente
from app.models.equipment import TipoEquipo, Componente, TipoEquipoComponente, EquipoInstalado
from datetime import date

app = create_app("development")

with app.app_context():
    db.create_all()
    print("Tablas creadas.")

    if not db.session.execute(select(Usuario).where(Usuario.email == "admin@watermax.ec")).scalars().first():
        admin = Usuario(
            nombre="Propietario Watermax",
            email="admin@watermax.ec",
            rol="propietario",
        )
        admin.set_password("Watermax2026!")
        db.session.add(admin)

    if not db.session.execute(select(Usuario).where(Usuario.email == "admin2@watermax.ec")).scalars().first():
        adm = Usuario(nombre="Administrativo Watermax", email="admin2@watermax.ec", rol="administrativo")
        adm.set_password("Watermax2026!")
        db.session.add(adm)

    if not db.session.execute(select(Usuario).where(Usuario.email == "tecnico@watermax.ec")).scalars().first():
        tec = Usuario(nombre="Técnico Watermax", email="tecnico@watermax.ec", rol="tecnico")
        tec.set_password("Watermax2026!")
        db.session.add(tec)

    zonas_nombres = ["Norte", "Sur", "Centro", "Este", "Oeste"]
    for nombre in zonas_nombres:
        if not db.session.execute(select(Zona).where(Zona.nombre == nombre)).scalars().first():
            db.session.add(Zona(nombre=nombre))

    if not db.session.execute(
        select(TipoEquipo).where(TipoEquipo.nombre == "Purificador Osmosis 5 etapas")
    ).scalars().first():
        tipo = TipoEquipo(nombre="Purificador Osmosis 5 etapas", marca="Genérico")
        db.session.add(tipo)
        db.session.flush()

        componentes_data = [
            ("Filtro de sedimento", 3),
            ("Filtro de carbón activado", 6),
            ("Filtro alcalino", 12),
            ("Membrana de ósmosis inversa", 24),
            ("Lámpara UV", 12),
        ]
        for nombre_comp, intervalo in componentes_data:
            comp = Componente(nombre=nombre_comp, intervalo_nominal=intervalo)
            db.session.add(comp)
            db.session.flush()
            db.session.add(TipoEquipoComponente(
                tipo_equipo_id=tipo.id,
                componente_id=comp.id,
            ))

    db.session.commit()
    print("Datos iniciales insertados.")
    print("\nCredenciales iniciales:")
    print("  Email:    admin@watermax.ec")
    print("  Password: Watermax2026!")
    print("\nCambia la contraseña en producción.")
    print("\n--- PASO SIGUIENTE ---")
    print("Ejecuta el siguiente comando para registrar las migraciones como aplicadas:")
    print("  flask db stamp head")
