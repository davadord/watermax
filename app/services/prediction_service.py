"""
Motor de predicción de vencimientos.
Combina el intervalo nominal del fabricante con el promedio
de ciclos reales del historial de intervenciones.
"""
from datetime import date, timedelta
from statistics import mean
from app.models.maintenance import DetalleMantenimiento, Mantenimiento


URGENCIA_VENCIDO = "vencido"
URGENCIA_PROXIMO = "proximo"      # <= 7 días
URGENCIA_EN_PLAZO = "en_plazo"


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
        intervalo_nominal = comp.intervalo_nominal  # meses

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

        # Calcular intervalo real si hay al menos 2 intervenciones
        fuente = "nominal"
        intervalo_dias = intervalo_nominal * 30  # aproximación

        if len(fechas) >= 2:
            ciclos_dias = [
                (fechas[i+1] - fechas[i]).days
                for i in range(len(fechas) - 1)
            ]
            intervalo_real = int(mean(ciclos_dias))
            # Usar historial si no difiere más del 50% del nominal
            if abs(intervalo_real - intervalo_dias) / intervalo_dias <= 0.5:
                intervalo_dias = intervalo_real
                fuente = "historico"

        ultima_fecha = fechas[-1] if fechas else equipo.fecha_instalacion
        fecha_proyectada = ultima_fecha + timedelta(days=intervalo_dias)
        dias_restantes = (fecha_proyectada - hoy).days

        if dias_restantes < 0:
            urgencia = URGENCIA_VENCIDO
        elif dias_restantes <= 7:
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
