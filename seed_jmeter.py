"""
Poblar BD con 2.000 equipos sintéticos para tests JMeter — issue #16.

Uso:
    python seed_jmeter.py              # development (local)
    python seed_jmeter.py production   # PythonAnywhere

Prerequisito: setup_db.py ejecutado (zonas + tipos + usuarios base).
Idempotente: si ya hay equipos WMX-* no inserta nada.
Al terminar imprime IDs y credenciales listos para JMeter.

Requiere: pip install Faker
"""
import sys
import random
from datetime import date, timedelta
from sqlalchemy import select, func

try:
    from faker import Faker
except ImportError:
    print("ERROR: instala Faker →  pip install Faker")
    sys.exit(1)

from app import create_app, db
from app.models.user import Usuario
from app.models.client import Zona, Cliente
from app.models.equipment import TipoEquipo, EquipoInstalado
from app.models.maintenance import Mantenimiento, DetalleMantenimiento

random.seed(42)
fake = Faker("es_ES")
fake.seed_instance(42)

CONFIG = sys.argv[1] if len(sys.argv) > 1 else "development"
app = create_app(CONFIG)

# Norte = 50 equipos → escenario PDF (50 filas en el reporte de zona).
# El resto distribuye los 1.950 equipos entre las otras 4 zonas.
ZONA_DIST = {
    "Norte":        50,
    "Centro-Norte": 390,
    "Noroeste":     390,
    "Centro":       390,
    "Centro-Sur":   390,
    "Sur":          390,
}
TOTAL = sum(ZONA_DIST.values())  # 2.000
BATCH = 200

# ── Datos sintéticos realistas para Guayaquil ─────────────────────────────────

SECTORES = {
    "Norte":        ["Alborada", "Sauces", "Guayacanes", "Samanes", "Vergeles",
                     "Las Orquídeas", "Mucho Lote", "Garzota",
                     "Metrópolis", "Villa España"],
    "Centro-Norte": ["Urdesa Central", "Urdesa Norte", "Lomas de Urdesa",
                     "Kennedy Norte", "Kennedy Vieja", "Ciudadela Bolivariana",
                     "La Atarazana", "Ciudadela Universitaria",
                     "Orellana", "Simón Bolívar"],
    "Noroeste":     ["Mapasingue Este", "Mapasingue Oeste", "Prosperina",
                     "Bastión Popular", "Ceibos", "Los Olivos",
                     "Las Cumbres", "Colinas de los Ceibos",
                     "Bellavista", "Miraflores"],
    "Centro":       ["Centro de Guayaquil", "Las Peñas", "Cerro Santa Ana",
                     "Puerto Santa Ana", "Barrio del Astillero", "Centenario",
                     "Barrio Garay", "Cuba", "Del Salado", "9 de Octubre"],
    "Centro-Sur":   ["La Saiba", "La Floresta", "Pradera", "Las Acacias",
                     "Los Esteros", "Sopeña", "Ciudadela 9 de Octubre",
                     "Huancavilca Sur", "Santa Mónica", "Las Tejas"],
    "Sur":          ["Guasmo Norte", "Guasmo Central", "Guasmo Sur",
                     "Isla Trinitaria", "Coviem", "Valdivia",
                     "Los Almendros", "25 de Julio",
                     "Unión de Bananeros", "Viernes Santo"],
}

DOMINIOS = ["gmail.com", "hotmail.com", "yahoo.es", "outlook.com"]


def _cedula_guayas():
    """Cédula ecuatoriana válida — provincia Guayas (09)."""
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


def _direccion(zona):
    sector = random.choice(SECTORES[zona])
    return f"{sector} {random.randint(1, 999)}, Guayaquil", sector


def _email(nombre):
    trans = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    partes = nombre.translate(trans).lower().split()
    user = f"{partes[0]}.{partes[-1]}" if len(partes) > 1 else partes[0]
    return f"{user}{random.randint(1, 99)}@{random.choice(DOMINIOS)}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    with app.app_context():
        _check_idempotency()

        tipos = db.session.execute(select(TipoEquipo)).scalars().all()
        if not tipos:
            print("ERROR: no hay tipos de equipo. Ejecuta setup_db.py primero.")
            sys.exit(1)

        tecnico = _get_tecnico()
        _ensure_4th_user()

        zonas = {z.nombre: z for z in db.session.execute(select(Zona)).scalars().all()}
        missing = [n for n in ZONA_DIST if n not in zonas]
        if missing:
            print(f"ERROR: zonas no encontradas: {missing}. Ejecuta setup_db.py primero.")
            sys.exit(1)

        cedulas = set()
        idx = 0

        for zona_nombre, count in ZONA_DIST.items():
            zona = zonas[zona_nombre]
            print(f"Insertando zona {zona_nombre} ({count} equipos)...")
            for _ in range(count):
                idx += 1
                tipo = tipos[idx % len(tipos)]
                _insert_equipo(idx, zona, tipo, tecnico, zona_nombre, cedulas)
                if idx % BATCH == 0:
                    db.session.commit()
                    print(f"  {idx}/{TOTAL}")

        db.session.commit()
        print(f"\nSeed completo: {idx} equipos insertados.")
        _print_summary()


def _insert_equipo(idx, zona, tipo, tecnico, zona_nombre, cedulas):
    nombre = fake.name()

    cedula = _cedula_guayas()
    while cedula in cedulas:
        cedula = _cedula_guayas()
    cedulas.add(cedula)

    direccion, sector = _direccion(zona_nombre)

    cliente = Cliente(
        nombre=nombre,
        tipo_identificador="Cédula",
        identificador=cedula,
        telefono=_telefono(),
        direccion=direccion,
        email=_email(nombre),
        activo=True,
    )
    db.session.add(cliente)
    db.session.flush()

    # Instalado hace 1–4 años (vida útil real de un purificador doméstico)
    fecha_inst = date.today() - timedelta(days=random.randint(365, 1460))

    equipo = EquipoInstalado(
        cliente_id=cliente.id,
        tipo_equipo_id=tipo.id,
        zona_id=zona.id,
        numero_serie=f"WMX-{idx:05d}",
        sector=sector,
        fecha_instalacion=fecha_inst,
        activo=True,
    )
    db.session.add(equipo)
    db.session.flush()

    componentes = [tec.componente for tec in tipo.componentes]
    _add_maintenance(equipo, componentes, tecnico, fecha_inst, idx)


def _add_maintenance(equipo, componentes, tecnico, fecha_inst, idx):
    """
    Distribución de historial de mantenimientos:
      40%  sin historial       → motor usa intervalo nominal desde fecha_inst
      35%  1 mantenimiento     → nominal con fecha base real
      25%  2-3 mantenimientos  → activa rama histórica de _intervalo_efectivo()

    Componentes con intervalo ≤ 8 meses reciben "reemplazo" garantizado
    para que existan ≥2 ciclos dentro del ±50% del nominal y se active
    la rama histórica del motor predictivo.
    """
    bucket = idx % 20          # 0-7 = 40%,  8-14 = 35%,  15-19 = 25%
    if bucket < 8:
        return
    n_mant = 1 if bucket < 15 else random.choice([2, 2, 3])

    # Ciclo base: Filtro de sedimento = 4 meses = 120 días (más corto del catálogo)
    comp_base = next(
        (c for c in componentes if c.nombre == "Filtro de sedimento"),
        componentes[0],
    )
    ciclo = comp_base.intervalo_nominal * 30  # 120 días

    fecha = fecha_inst + timedelta(days=random.randint(110, 130))

    for _ in range(n_mant):
        if fecha >= date.today():
            break

        mant = Mantenimiento(
            equipo_id=equipo.id,
            tecnico_id=tecnico.id,
            fecha=fecha,
            completado=True,
        )
        db.session.add(mant)
        db.session.flush()

        for comp in componentes:
            accion = (
                "reemplazo"
                if comp.intervalo_nominal <= 8
                else random.choice(["reemplazo", "limpieza", "revision"])
            )
            proximo = (
                fecha + timedelta(days=comp.intervalo_nominal * 30)
                if accion == "reemplazo" else None
            )
            db.session.add(DetalleMantenimiento(
                mantenimiento_id=mant.id,
                componente_id=comp.id,
                accion=accion,
                proximo_mantenimiento=proximo,
            ))

        fecha += timedelta(days=ciclo + random.randint(-10, 10))


# ── Prerequisitos ─────────────────────────────────────────────────────────────

def _check_idempotency():
    count = db.session.execute(
        select(func.count(EquipoInstalado.id)).where(
            EquipoInstalado.numero_serie.like("WMX-%")
        )
    ).scalar()
    if count >= TOTAL:
        print(f"Seed ya aplicado ({count} equipos WMX). Nada que insertar.")
        _print_summary()
        sys.exit(0)
    if 0 < count < TOTAL:
        print(f"ADVERTENCIA: seed parcial ({count}/{TOTAL} equipos WMX). Limpia y re-ejecuta.")
        sys.exit(1)


def _get_tecnico():
    t = db.session.execute(
        select(Usuario).where(Usuario.email == "tecnico@watermax.ec")
    ).scalars().first()
    if not t:
        print("ERROR: tecnico@watermax.ec no encontrado. Ejecuta setup_db.py primero.")
        sys.exit(1)
    return t


def _ensure_4th_user():
    if not db.session.execute(
        select(Usuario).where(Usuario.email == "tecnico2@watermax.ec")
    ).scalars().first():
        u = Usuario(nombre="Técnico 2 Watermax", email="tecnico2@watermax.ec", rol="tecnico")
        u.set_password("Watermax2026!")
        db.session.add(u)
        db.session.flush()
        print("Usuario tecnico2@watermax.ec creado.")


# ── Resumen ───────────────────────────────────────────────────────────────────

def _print_summary():
    zona_pdf = db.session.execute(
        select(Zona).where(Zona.nombre == "Norte")
    ).scalars().first()

    total_act = db.session.execute(
        select(func.count(EquipoInstalado.id)).where(EquipoInstalado.activo == True)
    ).scalar()

    pdf_count = (
        db.session.execute(
            select(func.count(EquipoInstalado.id)).where(
                EquipoInstalado.zona_id == zona_pdf.id,
                EquipoInstalado.activo == True,
            )
        ).scalar()
        if zona_pdf else "?"
    )
    pdf_id = zona_pdf.id if zona_pdf else "?"

    sep = "=" * 58
    print(f"\n{sep}")
    print("  JMeter Seed - Configuracion lista")
    print(sep)
    print(f"  Equipos activos totales : {total_act}")
    print(f"  Zona Norte (PDF test)   : id={pdf_id} - {pdf_count} equipos")
    print()
    print("  Credenciales - 4 threads JMeter:")
    print("    Thread 1  admin@watermax.ec     / Watermax2026!")
    print("    Thread 2  admin2@watermax.ec    / Watermax2026!")
    print("    Thread 3  tecnico@watermax.ec   / Watermax2026!")
    print("    Thread 4  tecnico2@watermax.ec  / Watermax2026!")
    print()
    print("  Endpoints:")
    print("    POST /auth/login")
    print("    GET  /reports/dashboard           (escenario 1: 2.000 equipos)")
    print(f"    GET  /reports/zona/{pdf_id}/pdf          (escenario 2: PDF 50 registros)")
    print(sep)


if __name__ == "__main__":
    main()
