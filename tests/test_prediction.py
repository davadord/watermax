"""
Pruebas de caracterización del motor predictivo (app/services/prediction_service.py).

Verifican el comportamiento que YA existe, con los valores reales del código:
- intervalo nominal en MESES, convertido a días con *30 (D2).
- umbral de alerta = 15 días (UMBRAL_ALERTA_DIAS), límites exactos.
- histórico solo si ≥ 2 reemplazos y desviación ≤ 50% del nominal (D4).
- solo accion == "reemplazo" reinicia el reloj predictivo (D3).

Todas las pruebas fijan las fechas con fecha_ref o con fechas absolutas, de modo
que no dependen de date.today() ni del orden de ejecución.
"""
from datetime import date, timedelta

import pytest

from app.services.prediction_service import (
    calcular_vencimientos,
    calcular_proximo_componente,
    _intervalo_efectivo,
    URGENCIA_VENCIDO,
    URGENCIA_PROXIMO,
    URGENCIA_EN_PLAZO,
    UMBRAL_ALERTA_DIAS,
)

NOMINAL_MESES = 6
NOMINAL_DIAS = NOMINAL_MESES * 30  # 180


def _equipo_con_un_componente(factory, fecha_instalacion, fecha_reactivacion=None,
                              nominal_meses=NOMINAL_MESES):
    comp = factory.componente(intervalo_nominal_meses=nominal_meses)
    tipo = factory.tipo_equipo(componentes=[comp])
    eq = factory.equipo(
        tipo_equipo=tipo,
        fecha_instalacion=fecha_instalacion,
        fecha_reactivacion=fecha_reactivacion,
    )
    return eq, comp


# ---------------------------------------------------------------------------
# calcular_vencimientos: proyección sin historial
# ---------------------------------------------------------------------------

def test_calcular_vencimientos_sin_historial_proyecta_con_intervalo_nominal(factory):
    instalacion = date(2025, 1, 1)
    eq, comp = _equipo_con_un_componente(factory, instalacion)

    resultado = calcular_vencimientos(eq, fecha_ref=instalacion)

    assert len(resultado) == 1
    item = resultado[0]
    assert item["componente"].id == comp.id
    assert item["fuente"] == "nominal"
    assert item["intervalo_usado"] == NOMINAL_DIAS
    assert item["fecha_proyectada"] == instalacion + timedelta(days=NOMINAL_DIAS)


def test_calcular_vencimientos_sin_historial_usa_fecha_instalacion_como_base(factory):
    instalacion = date(2025, 3, 10)
    eq, _ = _equipo_con_un_componente(factory, instalacion)

    item = calcular_vencimientos(eq, fecha_ref=instalacion)[0]

    assert item["fecha_proyectada"] == instalacion + timedelta(days=NOMINAL_DIAS)


# ---------------------------------------------------------------------------
# calcular_vencimientos: clasificación de urgencia en el límite exacto (15 días)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dias_restantes, urgencia_esperada", [
    (-1, URGENCIA_VENCIDO),                    # vencido: días negativos
    (0, URGENCIA_PROXIMO),                     # límite inferior de "próximo"
    (UMBRAL_ALERTA_DIAS, URGENCIA_PROXIMO),     # límite superior de "próximo" (15)
    (UMBRAL_ALERTA_DIAS + 1, URGENCIA_EN_PLAZO),  # primer día "en plazo" (16)
])
def test_clasificacion_de_urgencia_en_los_limites_del_umbral(factory, dias_restantes, urgencia_esperada):
    instalacion = date(2025, 1, 1)
    eq, _ = _equipo_con_un_componente(factory, instalacion)
    proyectada = instalacion + timedelta(days=NOMINAL_DIAS)

    item = calcular_vencimientos(eq, fecha_ref=proyectada - timedelta(days=dias_restantes))[0]

    assert item["dias_restantes"] == dias_restantes
    assert item["urgencia"] == urgencia_esperada


# ---------------------------------------------------------------------------
# calcular_vencimientos: efecto de fecha_ref al proyectar a futuro
# ---------------------------------------------------------------------------

def test_fecha_ref_futura_cambia_la_clasificacion_a_vencido(factory):
    instalacion = date(2025, 1, 1)
    eq, _ = _equipo_con_un_componente(factory, instalacion)

    en_instalacion = calcular_vencimientos(eq, fecha_ref=instalacion)[0]
    muy_futuro = calcular_vencimientos(eq, fecha_ref=date(2030, 1, 1))[0]

    assert en_instalacion["urgencia"] == URGENCIA_EN_PLAZO
    assert muy_futuro["urgencia"] == URGENCIA_VENCIDO
    # La fecha proyectada no depende de fecha_ref; solo cambia dias_restantes/urgencia.
    assert en_instalacion["fecha_proyectada"] == muy_futuro["fecha_proyectada"]


# ---------------------------------------------------------------------------
# _intervalo_efectivo: histórico vs nominal (umbral 50%, ≥ 2 reemplazos)
# ---------------------------------------------------------------------------

def test_intervalo_efectivo_sin_historial_retorna_nominal(factory):
    eq, comp = _equipo_con_un_componente(factory, date(2025, 1, 1))

    intervalo, fuente, ultima = _intervalo_efectivo(eq, comp)

    assert intervalo == NOMINAL_DIAS
    assert fuente == "nominal"
    assert ultima is None


def test_intervalo_efectivo_un_solo_reemplazo_no_alcanza_para_historico(factory):
    instalacion = date(2024, 1, 1)
    eq, comp = _equipo_con_un_componente(factory, instalacion)
    r0 = date(2024, 6, 1)
    factory.mantenimiento(eq, r0, [(comp, "reemplazo")])

    intervalo, fuente, ultima = _intervalo_efectivo(eq, comp)
    item = calcular_vencimientos(eq, fecha_ref=instalacion)[0]

    assert fuente == "nominal"
    assert intervalo == NOMINAL_DIAS
    assert ultima == r0
    # La proyección usa el único reemplazo (r0) como base, no la instalación.
    assert item["fecha_proyectada"] == r0 + timedelta(days=NOMINAL_DIAS)


def test_intervalo_efectivo_dos_ciclos_dentro_del_50pct_usa_historico(factory):
    eq, comp = _equipo_con_un_componente(factory, date(2024, 1, 1))
    r0 = date(2024, 1, 1)
    r1 = r0 + timedelta(days=200)
    r2 = r1 + timedelta(days=200)
    for f in (r0, r1, r2):
        factory.mantenimiento(eq, f, [(comp, "reemplazo")])

    intervalo, fuente, ultima = _intervalo_efectivo(eq, comp)

    # ciclos = [200, 200]; desviación |200-180|/180 = 0.11 ≤ 0.5 → histórico
    assert fuente == "historico"
    assert intervalo == 200
    assert ultima == r2


def test_intervalo_efectivo_desviacion_mayor_al_50pct_cae_a_nominal(factory):
    eq, comp = _equipo_con_un_componente(factory, date(2024, 1, 1))
    r0 = date(2024, 1, 1)
    r1 = r0 + timedelta(days=300)
    r2 = r1 + timedelta(days=300)
    for f in (r0, r1, r2):
        factory.mantenimiento(eq, f, [(comp, "reemplazo")])

    intervalo, fuente, ultima = _intervalo_efectivo(eq, comp)

    # ciclos = [300, 300]; desviación |300-180|/180 = 0.67 > 0.5 → nominal
    assert fuente == "nominal"
    assert intervalo == NOMINAL_DIAS
    assert ultima == r2  # la última fecha se reporta aun cayendo a nominal


# ---------------------------------------------------------------------------
# _intervalo_efectivo: filtros de la query (solo reemplazos válidos cuentan)
# ---------------------------------------------------------------------------

def test_la_limpieza_no_reinicia_el_reloj_ni_desplaza_la_fecha_proyectada(factory):
    instalacion = date(2024, 1, 1)
    eq, comp = _equipo_con_un_componente(factory, instalacion)
    reemplazo = date(2024, 6, 1)
    limpieza_posterior = date(2024, 9, 1)
    factory.mantenimiento(eq, reemplazo, [(comp, "reemplazo")])
    factory.mantenimiento(eq, limpieza_posterior, [(comp, "limpieza")])

    intervalo, fuente, ultima = _intervalo_efectivo(eq, comp)
    item = calcular_vencimientos(eq, fecha_ref=instalacion)[0]

    # La limpieza no cuenta: la última fecha que reinicia el reloj sigue
    # siendo el reemplazo, y la proyección se calcula desde ahí.
    assert ultima == reemplazo
    assert fuente == "nominal"  # solo 1 reemplazo válido
    assert item["fecha_proyectada"] == reemplazo + timedelta(days=NOMINAL_DIAS)


@pytest.mark.parametrize("kwargs_invalidos", [
    {"motivo_anulacion": "anulado por error"},
    {"completado": False},
])
def test_reemplazo_anulado_o_no_completado_no_cuenta_en_el_historico(factory, kwargs_invalidos):
    eq, comp = _equipo_con_un_componente(factory, date(2024, 1, 1))
    r0 = date(2024, 1, 1)
    r1 = r0 + timedelta(days=200)
    factory.mantenimiento(eq, r0, [(comp, "reemplazo")])
    factory.mantenimiento(eq, r1, [(comp, "reemplazo")], **kwargs_invalidos)

    intervalo, fuente, ultima = _intervalo_efectivo(eq, comp)

    # Solo r0 es válido → no hay 2 ciclos → nominal, y la última válida es r0.
    assert fuente == "nominal"
    assert ultima == r0


# ---------------------------------------------------------------------------
# _intervalo_efectivo: fecha_reactivacion filtra reemplazos previos
# ---------------------------------------------------------------------------

def test_calcular_vencimientos_usa_reactivacion_como_base_si_es_posterior(factory):
    instalacion = date(2024, 1, 1)
    reactivacion = date(2025, 1, 1)
    eq, _ = _equipo_con_un_componente(
        factory, instalacion, fecha_reactivacion=reactivacion
    )

    item = calcular_vencimientos(eq, fecha_ref=reactivacion)[0]

    # Sin reemplazos: la base es max(instalacion, reactivacion) = reactivacion.
    assert item["fecha_proyectada"] == reactivacion + timedelta(days=NOMINAL_DIAS)


# ---------------------------------------------------------------------------
# calcular_proximo_componente: proyección al registrar una intervención
# ---------------------------------------------------------------------------

def test_calcular_proximo_componente_proyecta_desde_la_intervencion(factory):
    eq, comp = _equipo_con_un_componente(factory, date(2024, 1, 1))
    intervencion = date(2025, 2, 1)

    proximo = calcular_proximo_componente(eq, comp, intervencion)

    assert proximo == intervencion + timedelta(days=NOMINAL_DIAS)


def test_reemplazos_previos_a_la_reactivacion_se_descartan(factory):
    reactivacion = date(2025, 1, 1)
    eq, comp = _equipo_con_un_componente(
        factory, date(2023, 1, 1), fecha_reactivacion=reactivacion
    )
    factory.mantenimiento(eq, date(2024, 6, 1), [(comp, "reemplazo")])  # antes
    posterior = date(2025, 3, 1)
    factory.mantenimiento(eq, posterior, [(comp, "reemplazo")])  # después

    intervalo, fuente, ultima = _intervalo_efectivo(eq, comp)

    assert ultima == posterior  # el reemplazo previo a la reactivación se descartó
    assert fuente == "nominal"  # queda 1 solo reemplazo válido
