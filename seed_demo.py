"""
Seed de datos realistas para la evaluación de usabilidad (SUS, issue #17).

Genera un dataset con apariencia real (contexto Guayaquil/Ecuador): clientes
con cédulas/RUC de dígito verificador válido, catálogo real de productos
Watermax y un estado crítico CONTROLADO para que el dashboard, el listado de
equipos críticos y los PDF tengan contenido predecible durante las sesiones:

    4 equipos VENCIDOS · 3 PRÓXIMOS a vencer · 11 EN PLAZO

Preserva los usuarios (cuentas de login). Limpia y recrea el resto.
Uso:  python seed_demo.py

Equipo sugerido para la tarea T4 del guion (registrar mantenimiento sin
alterar el listado de críticos): el marcado como [T4] al final del resumen.
"""

import random
from datetime import date, timedelta

from app import create_app, db
from app.models.client import Cliente, Zona
from app.models.equipment import (
    Componente,
    EquipoInstalado,
    TipoEquipo,
    TipoEquipoComponente,
)
from app.models.maintenance import DetalleMantenimiento, Mantenimiento
from app.models.user import Usuario

TODAY = date.today()
random.seed(17)  # determinista: mismo dataset en cada corrida (issue #17)

# El motor predictivo proyecta desde el último "reemplazo" + intervalo nominal
# del componente; el de menor intervalo (sedimento, 4 meses = 120 d) manda la
# urgencia. Controlamos el estado vía "días desde el último reemplazo":
OFFSET_POR_URGENCIA = {
    "vencido": lambda: random.randint(150, 205),  # sedimento vencido 30-85 d
    "proximo": lambda: random.randint(106, 118),  # vence en 2-14 d (umbral 15)
    "ok":      lambda: random.randint(20, 95),     # > 15 d restantes
}


# ---------------------------------------------------------------------------
# Validación de identificadores ecuatorianos (dígito verificador real)
# ---------------------------------------------------------------------------

def _dv_cedula(nueve: str) -> int:
    coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for c, k in zip(nueve, coef):
        p = int(c) * k
        total += p - 9 if p > 9 else p
    return (10 - (total % 10)) % 10


def _cedula(tercer: int, resto: int) -> str:
    """Cédula válida: 09 (Guayas) + tercer dígito (0-5) + 6 dígitos + verificador."""
    nueve = f"09{tercer}{resto % 1000000:06d}"
    return nueve + str(_dv_cedula(nueve))


def _dv_ruc_sociedad(nueve: str) -> int:
    coef = [4, 3, 2, 7, 6, 5, 4, 3, 2]
    r = sum(int(c) * k for c, k in zip(nueve, coef)) % 11
    return 0 if r == 0 else 11 - r


def _ruc_sociedad(resto: int) -> str:
    """RUC de sociedad privada: 09 + 9 + 6 dígitos + verificador + 001."""
    resto %= 1000000
    while True:
        nueve = f"099{resto:06d}"
        d = _dv_ruc_sociedad(nueve)
        if d != 10:
            return nueve + str(d) + "001"
        resto = (resto + 1) % 1000000


def _ruc_natural(tercer: int, resto: int) -> str:
    """RUC de persona natural: la cédula válida + 001."""
    return _cedula(tercer, resto) + "001"


# ---------------------------------------------------------------------------
# Catálogo (componentes y tipos de equipo reales de Watermax)
# ---------------------------------------------------------------------------

# nombre -> intervalo nominal en MESES
COMPONENTES_DEF = {
    "Filtro de sedimento":          4,
    "Filtro Cascara de coco T33":   8,
    "Filtro de carbón activado":   12,
    "Filtro de carbon de bloque":  12,
    "Filtro alcalino":             12,
    "Lámpara UV 6w":               12,
    "Membrana de ósmosis inversa": 24,
}

TIPOS_EQUIPO_DEF = {
    "OSMOSIS INVERSA 100 GPD UV": ("Genérico", [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de carbon de bloque", "Filtro de sedimento", "Lámpara UV 6w",
        "Membrana de ósmosis inversa",
    ]),
    "OSMOSIS INVERSA 100 GPD": (None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de carbon de bloque", "Filtro de sedimento", "Membrana de ósmosis inversa",
    ]),
    "PURIFICADOR W14 UV": (None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de carbon de bloque", "Filtro de sedimento", "Lámpara UV 6w",
    ]),
    "PURIFICADOR W14": (None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de carbon de bloque", "Filtro de sedimento",
    ]),
    "PURIFICADOR W13 UV": (None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de sedimento", "Lámpara UV 6w",
    ]),
    "BEBEDERO AGUA FRIA W13 UV": (None, [
        "Filtro alcalino", "Filtro Cascara de coco T33", "Filtro de carbón activado",
        "Filtro de sedimento", "Lámpara UV 6w",
    ]),
}

ZONAS = [
    ("Norte",          "Alborada, Sauces, Guayacanes, Garzota"),
    ("Centro",         "Centro de la ciudad y zona bancaria"),
    ("Sur",            "Guasmo, Centenario, Floresta"),
    ("Vía a la Costa", "Puerto Azul, Belo Horizonte, km 1-15"),
    ("Vía a Daule",    "Parque industrial, Pascuales"),
    ("Samborondón",    "La Puntilla, Entre Ríos"),
]

# ---------------------------------------------------------------------------
# Clientes (doc: 'ced' | 'ruc_nat' | 'ruc_soc')
# ---------------------------------------------------------------------------

CLIENTES_DEF = [
    {"nombre": "Cevichería El Manaba",            "doc": "ruc_nat", "zona": "Sur",            "tel": "0991840372", "dir": "Guasmo Sur, Coop. Unión de Bananeros Mz 14",       "email": "elmanaba.gye@gmail.com"},
    {"nombre": "Farmacia San José",               "doc": "ruc_nat", "zona": "Centro",         "tel": "042394118",  "dir": "Av. 9 de Octubre y Esmeraldas, local 3",           "email": "ventas@farmaciasanjose.ec"},
    {"nombre": "Hotel Boca del Río S.A.",         "doc": "ruc_soc", "zona": "Vía a la Costa", "dir": "Vía a la Costa km 10.5, Puerto Azul",              "tel": "042872550",  "email": "reservas@hotelbocadelrio.com"},
    {"nombre": "Panadería Su Pan",                "doc": "ruc_nat", "zona": "Norte",          "tel": "0982017744", "dir": "Cdla. Alborada XII, Mz 8 Villa 21",                "email": "panaderiasupan@hotmail.com"},
    {"nombre": "Distribuidora Aqua Vida S.A.",    "doc": "ruc_soc", "zona": "Vía a Daule",    "dir": "Parque Industrial Pascuales, nave 7",              "tel": "042103880",  "email": "info@aquavida.com.ec"},
    {"nombre": "Clínica Dental Sonríe",           "doc": "ruc_nat", "zona": "Norte",          "tel": "0995620148", "dir": "Cdla. Garzota, Av. Agustín Freire y 1ra",          "email": "citas@dentalsonrie.ec"},
    {"nombre": "Restaurante Sabor Costeño",       "doc": "ruc_nat", "zona": "Centro",         "tel": "042563071",  "dir": "Calle Boyacá 1623 y Luque",                        "email": "saborcosteno.gye@gmail.com"},
    {"nombre": "Gimnasio Energy Fit",             "doc": "ruc_nat", "zona": "Samborondón",    "tel": "0993008811", "dir": "Samborondón, C.C. La Piazza, local 12",            "email": "contacto@energyfit.ec"},
    {"nombre": "Jorge Cedeño Macías",             "doc": "ced",     "zona": "Norte",          "tel": "0991002345", "dir": "Cdla. Sauces 4, Mz 320 Villa 9",                   "email": "jorge.cedeno@gmail.com"},
    {"nombre": "María Fernanda Vera Solórzano",   "doc": "ced",     "zona": "Sur",            "tel": "0987551290", "dir": "Centenario, calle Venezuela 410",                  "email": "mfvera@outlook.com"},
    {"nombre": "Carlos Zambrano Ponce",           "doc": "ced",     "zona": "Vía a la Costa", "tel": "0962240178", "dir": "Belo Horizonte, etapa 2 Mz 5",                     "email": "carlos.zambrano@gmail.com"},
    {"nombre": "Gabriela Mora Bravo",             "doc": "ced",     "zona": "Samborondón",    "tel": "0984419063", "dir": "La Puntilla, urb. Ciudad Celeste, Cataluña 22",    "email": "gaby.mora@gmail.com"},
    {"nombre": "Luis Alberto Game Cabrera",       "doc": "ced",     "zona": "Centro",         "tel": "0991778204", "dir": "Urdesa Central, Av. V. E. Estrada 512",            "email": "luis.game@yahoo.com"},
]

# (cliente, tipo_equipo, sector, numero_serie, urgencia_objetivo)
EQUIPOS_DEF = [
    ("Cevichería El Manaba",          "PURIFICADOR W14 UV",        "Cocina",            "WM-22-0148", "vencido"),
    ("Cevichería El Manaba",          "BEBEDERO AGUA FRIA W13 UV", "Área de clientes",  "WM-23-0461", "ok"),
    ("Farmacia San José",             "PURIFICADOR W13 UV",        "Mostrador",         "WM-22-0307", "proximo"),
    ("Farmacia San José",             "BEBEDERO AGUA FRIA W13 UV", "Sala de espera",    "WM-24-0093", "ok"),
    ("Hotel Boca del Río S.A.",       "OSMOSIS INVERSA 100 GPD UV","Cocina central",    "WM-21-0052", "ok"),
    ("Hotel Boca del Río S.A.",       "BEBEDERO AGUA FRIA W13 UV", "Lobby",             "WM-23-0588", "ok"),
    ("Hotel Boca del Río S.A.",       "PURIFICADOR W14 UV",        "Restaurante",       "WM-23-0590", "ok"),
    ("Panadería Su Pan",              "PURIFICADOR W14",           "Producción",        "WM-22-0211", "vencido"),
    ("Distribuidora Aqua Vida S.A.",  "OSMOSIS INVERSA 100 GPD",   "Planta de llenado", "WM-20-0014", "ok"),
    ("Distribuidora Aqua Vida S.A.",  "OSMOSIS INVERSA 100 GPD UV","Línea embotellado", "WM-21-0077", "proximo"),
    ("Clínica Dental Sonríe",         "PURIFICADOR W14 UV",        "Consultorio 1",     "WM-23-0402", "ok"),
    ("Restaurante Sabor Costeño",     "PURIFICADOR W14",           "Cocina",            "WM-22-0259", "vencido"),
    ("Gimnasio Energy Fit",           "BEBEDERO AGUA FRIA W13 UV", "Sala de máquinas",  "WM-24-0120", "ok"),
    ("Jorge Cedeño Macías",           "PURIFICADOR W13 UV",        "Hogar",             "WM-24-0188", "ok"),
    ("María Fernanda Vera Solórzano", "PURIFICADOR W14",           "Hogar",             "WM-23-0334", "proximo"),
    ("Carlos Zambrano Ponce",         "OSMOSIS INVERSA 100 GPD",   "Hogar",             "WM-22-0501", "ok"),
    ("Gabriela Mora Bravo",           "PURIFICADOR W14 UV",        "Hogar",             "WM-24-0205", "ok"),
    ("Luis Alberto Game Cabrera",     "PURIFICADOR W13 UV",        "Hogar",             "WM-21-0033", "vencido"),
]

OBS_REEMPLAZO = [
    "Mantenimiento preventivo: cambio de filtros y revisión de fugas.",
    "Reemplazo de etapas de filtración. Equipo operativo.",
    "Cambio general de filtros. Se verifica presión y caudal.",
    "Mantenimiento programado. Sin novedades en la instalación.",
]
OBS_REVISION = [
    "Visita de revisión. Filtros en buen estado.",
    "Limpieza de carcazas y revisión de conexiones.",
    "Inspección de rutina. Se recomienda cambio en próxima visita.",
]


# ---------------------------------------------------------------------------
# Fases
# ---------------------------------------------------------------------------

def limpiar(session):
    print("  Limpiando datos (se preservan los usuarios)...")
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
    for nombre, desc in ZONAS:
        z = Zona(nombre=nombre, descripcion=desc)
        session.add(z)
        zonas[nombre] = z

    componentes = {}
    for nombre, intervalo in COMPONENTES_DEF.items():
        c = Componente(nombre=nombre, intervalo_nominal=intervalo)
        session.add(c)
        componentes[nombre] = c
    session.flush()

    tipos = {}
    comps_de_tipo = {}
    for nombre, (marca, comp_nombres) in TIPOS_EQUIPO_DEF.items():
        t = TipoEquipo(nombre=nombre, marca=marca)
        session.add(t)
        session.flush()
        for cn in comp_nombres:
            session.add(TipoEquipoComponente(tipo_equipo_id=t.id, componente_id=componentes[cn].id))
        tipos[nombre] = t
        comps_de_tipo[nombre] = [componentes[cn] for cn in comp_nombres]

    session.flush()
    print(f"  {len(zonas)} zonas, {len(tipos)} tipos de equipo, {len(componentes)} componentes.")
    return zonas, tipos, comps_de_tipo


def crear_clientes(session, zonas):
    clientes = {}
    seq = 230415
    tercer = 0
    for c in CLIENTES_DEF:
        if c["doc"] == "ced":
            ident = _cedula(tercer, seq)
            tipo_ident = "Cédula"
        elif c["doc"] == "ruc_nat":
            ident = _ruc_natural(tercer, seq)
            tipo_ident = "RUC"
        else:
            ident = _ruc_sociedad(seq)
            tipo_ident = "RUC"
        seq += 81731
        tercer = (tercer + 1) % 6

        cliente = Cliente(
            nombre=c["nombre"],
            tipo_identificador=tipo_ident,
            identificador=ident,
            telefono=c["tel"],
            direccion=c["dir"],
            email=c["email"],
            activo=True,
        )
        session.add(cliente)
        clientes[c["nombre"]] = (cliente, zonas[c["zona"]])
    session.flush()
    print(f"  {len(clientes)} clientes.")
    return clientes


def crear_equipos(session, clientes, tipos):
    equipos_meta = []  # (equipo, comps, urgencia)
    for (cli_nombre, tipo_nombre, sector, serie, urgencia) in EQUIPOS_DEF:
        cliente, zona = clientes[cli_nombre]
        offset = OFFSET_POR_URGENCIA[urgencia]()
        instalacion = TODAY - timedelta(days=offset + random.randint(380, 760))
        eq = EquipoInstalado(
            cliente_id=cliente.id,
            tipo_equipo_id=tipos[tipo_nombre].id,
            zona_id=zona.id,
            sector=sector,
            numero_serie=serie,
            fecha_instalacion=instalacion,
            activo=True,
        )
        session.add(eq)
        equipos_meta.append((eq, tipo_nombre, urgencia, offset))
    session.flush()
    print(f"  {len(equipos_meta)} equipos instalados.")
    return equipos_meta


def crear_historicos(session, equipos_meta, comps_de_tipo, tecnico_id):
    mants = detalles = 0
    for eq, tipo_nombre, urgencia, offset in equipos_meta:
        comps = comps_de_tipo[tipo_nombre]

        # Visitas previas de revisión/limpieza (no son "reemplazo": no alteran
        # el cálculo de intervalo, solo dan historial realista).
        for j in range(random.choice([1, 2]), 0, -1):
            fecha = TODAY - timedelta(days=offset + 120 * j + random.randint(0, 25))
            if fecha < eq.fecha_instalacion:
                continue
            m = Mantenimiento(equipo_id=eq.id, tecnico_id=tecnico_id, fecha=fecha,
                              observaciones=random.choice(OBS_REVISION), completado=True)
            session.add(m)
            session.flush()
            for comp in comps:
                session.add(DetalleMantenimiento(
                    mantenimiento_id=m.id, componente_id=comp.id,
                    accion=random.choice(["revision", "limpieza"]), notas="",
                    proximo_mantenimiento=fecha + timedelta(days=comp.intervalo_nominal * 30),
                ))
                detalles += 1
            mants += 1

        # Último servicio: reemplazo completo (controla la urgencia del equipo).
        fecha = TODAY - timedelta(days=offset)
        m = Mantenimiento(equipo_id=eq.id, tecnico_id=tecnico_id, fecha=fecha,
                          observaciones=random.choice(OBS_REEMPLAZO), completado=True)
        session.add(m)
        session.flush()
        for comp in comps:
            session.add(DetalleMantenimiento(
                mantenimiento_id=m.id, componente_id=comp.id,
                accion="reemplazo", notas="",
                proximo_mantenimiento=fecha + timedelta(days=comp.intervalo_nominal * 30),
            ))
            detalles += 1
        mants += 1
    return mants, detalles


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def seed():
    app = create_app()
    with app.app_context():
        tecnico = (
            db.session.query(Usuario).filter_by(rol="tecnico", activo=True).first()
            or db.session.query(Usuario).filter_by(activo=True).first()
        )
        if not tecnico:
            print("ERROR: no hay usuarios en la BD. Corre primero setup_db.py.")
            return

        print(f"\n=== Seed demo SUS (#17) — técnico de históricos: {tecnico.nombre} ===\n")
        print("[1/4] Limpiando...")
        limpiar(db.session)
        print("[2/4] Catálogo...")
        zonas, tipos, comps_de_tipo = crear_catalogo(db.session)
        print("[3/4] Clientes y equipos...")
        clientes = crear_clientes(db.session, zonas)
        equipos_meta = crear_equipos(db.session, clientes, tipos)
        print("[4/4] Históricos de mantenimiento...")
        mants, detalles = crear_historicos(db.session, equipos_meta, comps_de_tipo, tecnico.id)
        db.session.commit()

        venc = sum(1 for _, _, u, _ in equipos_meta if u == "vencido")
        prox = sum(1 for _, _, u, _ in equipos_meta if u == "proximo")
        ok = sum(1 for _, _, u, _ in equipos_meta if u == "ok")
        t4 = next((eq for eq, tn, u, _ in equipos_meta if u == "ok" and tn == "PURIFICADOR W13 UV"), None)

        print("\n=== Resultado ===")
        print(f"  Clientes              : {len(clientes)}")
        print(f"  Equipos instalados    : {len(equipos_meta)}")
        print(f"  Mantenimientos        : {mants}  ·  Detalles: {detalles}")
        print(f"\n  Estado crítico esperado en el dashboard:")
        print(f"    Vencidos : {venc}")
        print(f"    Próximos : {prox}  (<= 15 días)")
        print(f"    En plazo : {ok}")
        if t4:
            print(f"\n  [T4] Equipo sugerido para registrar mantenimiento en la prueba:")
            print(f"       serie {t4.numero_serie} (en plazo; no altera el listado de críticos)")
        print()


if __name__ == "__main__":
    seed()
