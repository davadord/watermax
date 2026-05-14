"""
Motor de predicción de vencimientos.
Combina el intervalo nominal del fabricante con el promedio
de ciclos reales del historial de intervenciones.
"""
from datetime import date, timedelta
from statistics import mean
from sqlalchemy.orm import joinedload
from app.models.maintenance import DetalleMantenimiento, Mantenimiento
from app.models.equipment import EquipoInstalado, TipoEquipo, TipoEquipoComponente


URGENCIA_VENCIDO = "vencido"
URGENCIA_PROXIMO = "proximo"
URGENCIA_EN_PLAZO = "en_plazo"

UMBRAL_ALERTA_DIAS = 15  # componentes con <= este valor se marcan como próximos


def calcular_vencimientos(equipo):
    """
    Retorna una lista de dicts con la proyección por componente:
    {
        componente, fecha_proyectada, urgencia, dias_restantes,
        intervalo_usado, fuente ('historico' | 'nominal')
    }
    """
    resultados = []
    hoy = date.today()

    for tec in equipo.tipo_equipo.componentes:
        comp = tec.componente
        intervalo_nominal = comp.intervalo_nominal  # días

        # Solo reemplazo resetea el reloj — limpieza y revision no cuentan
        historial = (
            DetalleMantenimiento.query
            .join(Mantenimiento)
            .filter(
                Mantenimiento.equipo_id == equipo.id,
                Mantenimiento.completado == True,
                DetalleMantenimiento.componente_id == comp.id,
                DetalleMantenimiento.accion == "reemplazo",
            )
            .order_by(Mantenimiento.fecha)
            .all()
        )

        fechas = [d.mantenimiento.fecha for d in historial]

        # Si el equipo fue reactivado, descartar historial anterior a la reactivación
        fecha_base = equipo.fecha_instalacion
        if equipo.fecha_reactivacion:
            fecha_base = max(equipo.fecha_instalacion, equipo.fecha_reactivacion)
            fechas = [f for f in fechas if f >= equipo.fecha_reactivacion]

        fuente = "nominal"
        intervalo_dias = intervalo_nominal * 30

        if len(fechas) >= 2:
            ciclos_dias = [
                (fechas[i+1] - fechas[i]).days
                for i in range(len(fechas) - 1)
            ]
            intervalo_real = int(mean(ciclos_dias))
            if abs(intervalo_real - intervalo_dias) / intervalo_dias <= 0.5:
                intervalo_dias = intervalo_real
                fuente = "historico"

        ultima_fecha = fechas[-1] if fechas else fecha_base
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

    # Ordenar: vencidos primero, luego próximos, luego en plazo
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
    intervalo_nominal_dias = componente.intervalo_nominal * 30

    historial = (
        DetalleMantenimiento.query
        .join(Mantenimiento)
        .filter(
            Mantenimiento.equipo_id == equipo.id,
            Mantenimiento.completado == True,
            DetalleMantenimiento.componente_id == componente.id,
            DetalleMantenimiento.accion == "reemplazo",
        )
        .order_by(Mantenimiento.fecha)
        .all()
    )

    fechas = [d.mantenimiento.fecha for d in historial]

    if equipo.fecha_reactivacion:
        fechas = [f for f in fechas if f >= equipo.fecha_reactivacion]

    intervalo_dias = intervalo_nominal_dias
    if len(fechas) >= 2:
        ciclos_dias = [
            (fechas[i + 1] - fechas[i]).days
            for i in range(len(fechas) - 1)
        ]
        intervalo_real = int(mean(ciclos_dias))
        if abs(intervalo_real - intervalo_nominal_dias) / intervalo_nominal_dias <= 0.5:
            intervalo_dias = intervalo_real

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

    query = (
        EquipoInstalado.query
        .filter_by(activo=True)
        .options(
            joinedload(EquipoInstalado.tipo_equipo)
                .joinedload(TipoEquipo.componentes)
                .joinedload(TipoEquipoComponente.componente),
            joinedload(EquipoInstalado.zona),
            joinedload(EquipoInstalado.cliente),
        )
    )
    if zona_id:
        query = query.filter_by(zona_id=zona_id)

    equipos = query.all()

    resultado = []
    for equipo in equipos:
        vencimientos = calcular_vencimientos(equipo)
        criticos = [
            v for v in vencimientos
            if v["urgencia"] in (URGENCIA_VENCIDO, URGENCIA_PROXIMO)
        ]
        if not criticos:
            continue

        # Filtro opcional por urgencia exacta
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
