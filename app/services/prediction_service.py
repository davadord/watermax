from datetime import date, timedelta
from statistics import mean
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app import db
from app.models.maintenance import DetalleMantenimiento, Mantenimiento
from app.models.equipment import EquipoInstalado, TipoEquipo, TipoEquipoComponente


URGENCIA_VENCIDO = "vencido"
URGENCIA_PROXIMO = "proximo"
URGENCIA_EN_PLAZO = "en_plazo"

UMBRAL_ALERTA_DIAS = 15


def _intervalo_efectivo(equipo, componente):
    """
    Retorna (intervalo_dias, fuente, ultima_fecha_reemplazo).
    fuente='historico' si ≥ 2 ciclos con desviación ≤ 50% del nominal; 'nominal' si no.
    ultima_fecha_reemplazo es el date del último reemplazo filtrado, o None si no hay.
    """
    intervalo_nominal = componente.intervalo_nominal * 30

    stmt = (
        select(DetalleMantenimiento)
        .join(Mantenimiento)
        .where(
            Mantenimiento.equipo_id == equipo.id,
            Mantenimiento.completado == True,
            Mantenimiento.motivo_anulacion == None,
            DetalleMantenimiento.componente_id == componente.id,
            DetalleMantenimiento.accion == "reemplazo",
        )
        .order_by(Mantenimiento.fecha)
    )
    historial = db.session.execute(stmt).scalars().all()
    fechas = [d.mantenimiento.fecha for d in historial]

    if equipo.fecha_reactivacion:
        fechas = [f for f in fechas if f >= equipo.fecha_reactivacion]

    ultima = fechas[-1] if fechas else None

    if len(fechas) >= 2 and intervalo_nominal > 0:
        ciclos_dias = [(fechas[i + 1] - fechas[i]).days for i in range(len(fechas) - 1)]
        intervalo_real = int(mean(ciclos_dias))
        if abs(intervalo_real - intervalo_nominal) / intervalo_nominal <= 0.5:
            return intervalo_real, "historico", ultima

    return intervalo_nominal, "nominal", ultima


def calcular_vencimientos(equipo, fecha_ref=None):
    """
    Retorna una lista de dicts con la proyección por componente:
    {
        componente, fecha_proyectada, urgencia, dias_restantes,
        intervalo_usado, fuente ('historico' | 'nominal')
    }
    fecha_ref permite proyectar al futuro (planificación). Por defecto: hoy.
    """
    resultados = []
    hoy = fecha_ref or date.today()

    for tec in equipo.tipo_equipo.componentes:
        comp = tec.componente

        intervalo_dias, fuente, ultima_reemplazo = _intervalo_efectivo(equipo, comp)

        fecha_base = equipo.fecha_instalacion
        if equipo.fecha_reactivacion:
            fecha_base = max(equipo.fecha_instalacion, equipo.fecha_reactivacion)

        ultima_fecha = ultima_reemplazo if ultima_reemplazo is not None else fecha_base
        fecha_proyectada = ultima_fecha + timedelta(days=intervalo_dias)
        dias_restantes = (fecha_proyectada - hoy).days

        if dias_restantes < 0:
            urgencia = URGENCIA_VENCIDO
        elif dias_restantes <= UMBRAL_ALERTA_DIAS:
            urgencia = URGENCIA_PROXIMO
        else:
            urgencia = URGENCIA_EN_PLAZO

        resultados.append({
            "componente": comp,
            "fecha_proyectada": fecha_proyectada,
            "urgencia": urgencia,
            "dias_restantes": dias_restantes,
            "intervalo_usado": intervalo_dias,
            "fuente": fuente,
        })

    orden = {URGENCIA_VENCIDO: 0, URGENCIA_PROXIMO: 1, URGENCIA_EN_PLAZO: 2}
    resultados.sort(key=lambda x: (orden[x["urgencia"]], x["dias_restantes"]))
    return resultados


def calcular_proximo_componente(equipo, componente, fecha_intervencion):
    """
    Calcula la fecha de próximo mantenimiento para un componente específico
    al momento de registrar una intervención. Excluye la intervención actual
    (aún no commiteada) del cálculo del promedio histórico.

    Retorna un objeto date.
    """
    intervalo_dias, _fuente, _ultima = _intervalo_efectivo(equipo, componente)
    return fecha_intervencion + timedelta(days=intervalo_dias)


def get_equipos_criticos(zona_id=None, urgencia=None):
    """
    Retorna lista de dicts para todos los equipos activos que tienen al menos
    un componente vencido o próximo a vencer.

    Carga relaciones con joinedload para evitar N+1 queries.
    Filtra opcionalmente por zona_id y/o urgencia ('vencido' | 'proximo').

    Cada dict:
    {
        equipo, urgencia_maxima, dias_min, componentes_criticos: [
            {componente, fecha_proyectada, urgencia, dias_restantes}
        ]
    }
    """
    orden_urgencia = {URGENCIA_VENCIDO: 0, URGENCIA_PROXIMO: 1, URGENCIA_EN_PLAZO: 2}

    stmt = (
        select(EquipoInstalado)
        .where(EquipoInstalado.activo == True)
        .options(
            joinedload(EquipoInstalado.tipo_equipo)
                .joinedload(TipoEquipo.componentes)
                .joinedload(TipoEquipoComponente.componente),
            joinedload(EquipoInstalado.zona),
            joinedload(EquipoInstalado.cliente),
        )
    )
    if zona_id:
        stmt = stmt.where(EquipoInstalado.zona_id == zona_id)

    equipos = db.session.execute(stmt).unique().scalars().all()

    resultado = []
    for equipo in equipos:
        vencimientos = calcular_vencimientos(equipo)
        criticos = [
            v for v in vencimientos
            if v["urgencia"] in (URGENCIA_VENCIDO, URGENCIA_PROXIMO)
        ]
        if not criticos:
            continue

        if urgencia and urgencia in (URGENCIA_VENCIDO, URGENCIA_PROXIMO):
            if not any(v["urgencia"] == urgencia for v in criticos):
                continue

        urgencia_maxima = min(criticos, key=lambda v: orden_urgencia[v["urgencia"]])["urgencia"]
        dias_min = min(v["dias_restantes"] for v in criticos)

        resultado.append({
            "equipo": equipo,
            "urgencia_maxima": urgencia_maxima,
            "dias_min": dias_min,
            "componentes_criticos": criticos,
        })

    resultado.sort(key=lambda x: (orden_urgencia[x["urgencia_maxima"]], x["dias_min"]))
    return resultado
