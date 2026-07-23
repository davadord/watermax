"""
Poblar BD con 500 equipos y varios años de historial de mantenimiento,
simulando operación real, para demos y reportes (ej. componentes cambiados).

Uso: python seed_operacion.py

Limpia y recrea: zonas, tipos de equipo, componentes, clientes, equipos,
mantenimientos. Requiere usuarios ya creados (setup_db.py / seed previos).
Requiere: pip install Faker
"""
import random
from datetime import date, timedelta

from faker import Faker

from app import create_app, db
from app.models.user import Usuario
from app.models.client import Zona, Cliente
from app.models.equipment import (
    Componente, EquipoInstalado, TipoEquipo, TipoEquipoComponente,
)
from app.models.maintenance import Mantenimiento, DetalleMantenimiento

random.seed(7)
fake = Faker("es_ES")
fake.seed_instance(7)

TODAY = date.today()
TOTAL_EQUIPOS = 500

ZONAS = [
    {"nombre": "Norte",   "descripcion": "Sector norte de la ciudad"},
    {"nombre": "Sur",     "descripcion": "Sector sur de la ciudad"},
    {"nombre": "Centro",  "descripcion": "Zona central y comercial"},
    {"nombre": "Oriente", "descripcion": "Parroquias orientales"},
]

# Densidad relativa de clientes por zona (Centro concentra más comercios).
ZONAS_PESO = {"Norte": 30, "Sur": 22, "Centro": 33, "Oriente": 15}

# componente_nombre → intervalo_nominal en meses
COMPONENTES_DEF = {
    "Membrana de ósmosis":       12,
    "Filtro de sedimento":        4,
    "Filtro de carbón activado":  6,
    "Filtro post-carbón":         6,
    "Lámpara UV":                12,
    "Cabezal de filtro":          6,
    "Válvula de paso":           12,
}

TIPOS_EQUIPO_DEF = [
    {
        "nombre": "Ósmosis Inversa 50 GPD", "marca": "AquaPure",
        "descripcion": "Sistema de 5 etapas con membrana RO",
        "componentes": ["Membrana de ósmosis", "Filtro de sedimento",
                         "Filtro de carbón activado", "Filtro post-carbón"],
    },
    {
        "nombre": "Ósmosis Inversa 100 GPD", "marca": "AquaPure",
        "descripcion": "Sistema industrial de alta capacidad con RO",
        "componentes": ["Membrana de ósmosis", "Filtro de sedimento",
                         "Filtro de carbón activado", "Filtro post-carbón",
                         "Válvula de paso"],
    },
    {
        "nombre": "Filtro UV 12W", "marca": "ClearWave",
        "descripcion": "Purificador ultravioleta sin ósmosis",
        "componentes": ["Lámpara UV", "Filtro de sedimento", "Válvula de paso"],
    },
    {
        "nombre": "Filtro de carbón multietapa", "marca": "HydroMax",
        "descripcion": "Filtro sin ósmosis para agua de red",
        "componentes": ["Filtro de sedimento", "Filtro de carbón activado",
                         "Filtro post-carbón", "Cabezal de filtro"],
    },
]

SECTORES = {
    "Norte":   ["Alborada", "Sauces", "Guayacanes", "Samanes", "Garzota"],
    "Sur":     ["Guasmo Norte", "Guasmo Sur", "Isla Trinitaria", "Coviem", "Los Almendros"],
    "Centro":  ["Centro de Guayaquil", "Las Peñas", "Centenario", "Cuba", "9 de Octubre"],
    "Oriente": ["Mapasingue Este", "Prosperina", "Bastión Popular", "Los Olivos", "Ceibos"],
}

DOMINIOS = ["gmail.com", "hotmail.com", "yahoo.es", "outlook.com"]


def _cedula_guayas():
    d = [0, 9, random.randint(0, 6)] + [random.randint(0, 9) for _ in range(6)]
    total = 0
    for i, v in enumerate(d):
        val = v * 2 if i % 2 == 0 else v
        total += val - 9 if val >= 10 else val
    return "".join(str(x) for x in d) + str((10 - total % 10) % 10)


def _telefono():
    if random.random() < 0.75:
        return f"09{random.randint(10000000, 99999999)}"
    return f"042{random.randint(100000, 999999)}"


def _email(nombre):
    trans = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    partes = nombre.translate(trans).lower().split()
    user = f"{partes[0]}.{partes[-1]}" if len(partes) > 1 else partes[0]
    return f"{user}{random.randint(1, 99)}@{random.choice(DOMINIOS)}"


def limpiar(session):
    print("  Limpiando mantenimientos, equipos, clientes y catálogo...")
    session.query(DetalleMantenimiento).delete()
    session.query(Mantenimiento).delete()
    session.query(EquipoInstalado).delete()
    session.query(Cliente).delete()
    session.query(TipoEquipoComponente).delete()
    session.query(TipoEquipo).delete()
    session.query(Componente).delete()
    session.query(Zona).delete()
    session.commit()


def crear_catalogo(session):
    zonas = {}
    for z in ZONAS:
        zona = Zona(nombre=z["nombre"], descripcion=z["descripcion"])
        session.add(zona)
        zonas[z["nombre"]] = zona

    componentes = {}
    for nombre, intervalo in COMPONENTES_DEF.items():
        c = Componente(nombre=nombre, intervalo_nominal=intervalo)
        session.add(c)
        componentes[nombre] = c

    session.flush()

    tipos = {}
    for t in TIPOS_EQUIPO_DEF:
        tipo = TipoEquipo(nombre=t["nombre"], marca=t["marca"], descripcion=t["descripcion"])
        session.add(tipo)
        session.flush()
        for cn in t["componentes"]:
            session.add(TipoEquipoComponente(tipo_equipo_id=tipo.id, componente_id=componentes[cn].id))
        tipos[t["nombre"]] = tipo

    session.flush()
    print(f"  {len(zonas)} zonas, {len(tipos)} tipos de equipo, {len(componentes)} componentes creados.")
    return zonas, tipos, componentes


def _crear_cliente(cedulas):
    nombre = fake.name()
    cedula = _cedula_guayas()
    while cedula in cedulas:
        cedula = _cedula_guayas()
    cedulas.add(cedula)
    return Cliente(
        nombre=nombre,
        tipo_identificador="Cédula",
        identificador=cedula,
        telefono=_telefono(),
        direccion=fake.street_address(),
        email=_email(nombre),
        activo=True,
    )


def _generar_historial(session, equipo, componentes_tipo, tecnico_ids):
    """Genera mantenimientos desde la instalación hasta hoy, con reemplazos
    cuando se cumple (aprox) el intervalo nominal de cada componente."""
    proximo_reemplazo = {c.id: equipo.fecha_instalacion + timedelta(days=c.intervalo_nominal * 30)
                          for c in componentes_tipo}

    fecha = equipo.fecha_instalacion + timedelta(days=random.randint(85, 130))
    while fecha < TODAY:
        mant = Mantenimiento(
            equipo_id=equipo.id,
            tecnico_id=random.choice(tecnico_ids),
            fecha=fecha,
            observaciones="Mantenimiento preventivo rutinario.",
            completado=True,
        )
        session.add(mant)
        session.flush()

        for comp in componentes_tipo:
            vencido = fecha >= proximo_reemplazo[comp.id] - timedelta(days=15)
            if vencido:
                accion = "reemplazo"
                proximo_reemplazo[comp.id] = fecha + timedelta(days=comp.intervalo_nominal * 30)
            else:
                accion = random.choice(["limpieza", "revision", "revision"])

            session.add(DetalleMantenimiento(
                mantenimiento_id=mant.id,
                componente_id=comp.id,
                accion=accion,
                proximo_mantenimiento=proximo_reemplazo[comp.id] if accion == "reemplazo" else None,
            ))

        fecha += timedelta(days=random.randint(85, 130))


def seed():
    app = create_app()
    with app.app_context():
        tecnicos = db.session.query(Usuario).filter_by(activo=True).all()
        if not tecnicos:
            print("ERROR: no hay usuarios en la BD. Ejecuta setup_db.py primero.")
            return
        tecnico_ids = [u.id for u in tecnicos]

        print(f"\n=== Seed operación real — {TOTAL_EQUIPOS} equipos ===\n")

        print("[1/3] Limpiando datos anteriores...")
        limpiar(db.session)

        print("[2/3] Creando catálogo (zonas, tipos, componentes)...")
        zonas, tipos, componentes = crear_catalogo(db.session)
        zonas_list = list(zonas.values())
        tipos_list = list(tipos.values())

        tipo_componentes = {
            tipo.id: [c for c in componentes.values()
                      if c.nombre in next(t for t in TIPOS_EQUIPO_DEF if t["nombre"] == tipo.nombre)["componentes"]]
            for tipo in tipos_list
        }

        print(f"\n[3/3] Creando {TOTAL_EQUIPOS} clientes, equipos e históricos...")
        cedulas = set()
        zonas_ponderadas = [zonas[z["nombre"]] for z in ZONAS]
        pesos_zona = [ZONAS_PESO[z["nombre"]] for z in ZONAS]
        for idx in range(1, TOTAL_EQUIPOS + 1):
            cliente = _crear_cliente(cedulas)
            db.session.add(cliente)
            db.session.flush()

            zona = random.choices(zonas_ponderadas, weights=pesos_zona, k=1)[0]
            tipo = tipos_list[idx % len(tipos_list)]
            zona_nombre = zona.nombre

            fecha_inst = TODAY - timedelta(days=random.randint(365, 365 * 5))
            equipo = EquipoInstalado(
                cliente_id=cliente.id,
                tipo_equipo_id=tipo.id,
                zona_id=zona.id,
                sector=random.choice(SECTORES[zona_nombre]),
                numero_serie=f"WMX-{idx:04d}",
                fecha_instalacion=fecha_inst,
                activo=True,
            )
            db.session.add(equipo)
            db.session.flush()

            _generar_historial(db.session, equipo, tipo_componentes[tipo.id], tecnico_ids)

            if idx % 50 == 0:
                db.session.commit()
                print(f"  {idx}/{TOTAL_EQUIPOS}")

        db.session.commit()

        total_mant = db.session.query(Mantenimiento).count()
        total_det = db.session.query(DetalleMantenimiento).count()
        total_reemplazos = db.session.query(DetalleMantenimiento).filter_by(accion="reemplazo").count()

        print(f"\n=== Resultado ===")
        print(f"  Equipos creados            : {TOTAL_EQUIPOS}")
        print(f"  Mantenimientos históricos  : {total_mant}")
        print(f"  Detalles de componentes    : {total_det}")
        print(f"  Reemplazos                 : {total_reemplazos}")
        print()


if __name__ == "__main__":
    seed()
