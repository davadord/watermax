"""
Pruebas de integración del motor predictivo bajo contexto de request real.

test_prediction.py cubre la lógica pura (_intervalo_efectivo, calcular_vencimientos)
llamada directamente. Este archivo cubre las rutas que dependen de
has_request_context()/flask.g y de la caché cross-request por proceso:
_get_historial_reemplazos_map, get_equipos_criticos y get_resumen_global.
"""
from datetime import date, timedelta

from app.services.prediction_service import (
    get_equipos_criticos,
    get_resumen_global,
    invalidar_cache_resumen_global,
    URGENCIA_VENCIDO,
    URGENCIA_PROXIMO,
)

NOMINAL_MESES = 6
NOMINAL_DIAS = NOMINAL_MESES * 30


def _equipo_vencido(factory, zona=None):
    instalacion = date.today() - timedelta(days=NOMINAL_DIAS + 10)
    comp = factory.componente(intervalo_nominal_meses=NOMINAL_MESES)
    tipo = factory.tipo_equipo(componentes=[comp])
    return factory.equipo(tipo_equipo=tipo, fecha_instalacion=instalacion, zona=zona), comp


def _equipo_en_plazo(factory, zona=None):
    instalacion = date.today()
    comp = factory.componente(intervalo_nominal_meses=NOMINAL_MESES)
    tipo = factory.tipo_equipo(componentes=[comp])
    return factory.equipo(tipo_equipo=tipo, fecha_instalacion=instalacion, zona=zona), comp


# ---------------------------------------------------------------------------
# _get_historial_reemplazos_map (vía _intervalo_efectivo dentro de una request)
# ---------------------------------------------------------------------------

def test_historial_reemplazos_se_precarga_en_contexto_de_request(app, factory):
    instalacion = date(2024, 1, 1)
    comp = factory.componente(intervalo_nominal_meses=NOMINAL_MESES)
    tipo = factory.tipo_equipo(componentes=[comp])
    eq = factory.equipo(tipo_equipo=tipo, fecha_instalacion=instalacion)

    r1 = instalacion + timedelta(days=170)
    r2 = r1 + timedelta(days=190)
    factory.mantenimiento(eq, r1, [(comp, "reemplazo")])
    factory.mantenimiento(eq, r2, [(comp, "reemplazo")])

    with app.test_request_context("/"):
        criticos = get_equipos_criticos(zona_id=eq.zona_id)
        assert len(criticos) == 1
        detalle = criticos[0]["componentes_criticos"][0]
        assert detalle["fuente"] == "historico"


def test_historial_reemplazos_map_cachea_por_request(app, factory):
    from flask import g
    from app.services.prediction_service import _get_historial_reemplazos_map

    with app.test_request_context("/"):
        mapa1 = _get_historial_reemplazos_map()
        mapa2 = _get_historial_reemplazos_map()
        assert mapa1 is mapa2
        assert mapa1 is g._historial_reemplazos


def test_historial_reemplazos_map_fuera_de_request_retorna_none():
    from app.services.prediction_service import _get_historial_reemplazos_map

    assert _get_historial_reemplazos_map() is None


# ---------------------------------------------------------------------------
# get_equipos_criticos
# ---------------------------------------------------------------------------

def test_get_equipos_criticos_excluye_equipos_en_plazo(app, factory):
    zona = factory.zona()
    _equipo_vencido(factory, zona=zona)
    _equipo_en_plazo(factory, zona=zona)

    with app.test_request_context("/"):
        criticos = get_equipos_criticos(zona_id=zona.id)

    assert len(criticos) == 1
    assert criticos[0]["urgencia_maxima"] == URGENCIA_VENCIDO


def test_get_equipos_criticos_filtra_por_zona(app, factory):
    zona_a = factory.zona()
    zona_b = factory.zona()
    _equipo_vencido(factory, zona=zona_a)
    _equipo_vencido(factory, zona=zona_b)

    with app.test_request_context("/"):
        criticos = get_equipos_criticos(zona_id=zona_a.id)

    assert len(criticos) == 1
    assert criticos[0]["equipo"].zona_id == zona_a.id


def test_get_equipos_criticos_filtra_por_urgencia(app, factory):
    zona = factory.zona()
    _equipo_vencido(factory, zona=zona)

    with app.test_request_context("/"):
        solo_proximos = get_equipos_criticos(zona_id=zona.id, urgencia=URGENCIA_PROXIMO)
        solo_vencidos = get_equipos_criticos(zona_id=zona.id, urgencia=URGENCIA_VENCIDO)

    assert solo_proximos == []
    assert len(solo_vencidos) == 1


def test_get_equipos_criticos_ignora_equipos_inactivos(app, factory):
    zona = factory.zona()
    instalacion = date.today() - timedelta(days=NOMINAL_DIAS + 10)
    comp = factory.componente(intervalo_nominal_meses=NOMINAL_MESES)
    tipo = factory.tipo_equipo(componentes=[comp])
    factory.equipo(tipo_equipo=tipo, fecha_instalacion=instalacion, zona=zona, activo=False)

    with app.test_request_context("/"):
        criticos = get_equipos_criticos(zona_id=zona.id)

    assert criticos == []


def test_get_equipos_criticos_with_detail_false_omite_relaciones_pero_mismo_resultado(app, factory):
    zona = factory.zona()
    _equipo_vencido(factory, zona=zona)

    with app.test_request_context("/"):
        con_detalle = get_equipos_criticos(zona_id=zona.id, with_detail=True)
        sin_detalle = get_equipos_criticos(zona_id=zona.id, with_detail=False)

    assert len(con_detalle) == len(sin_detalle) == 1
    assert con_detalle[0]["urgencia_maxima"] == sin_detalle[0]["urgencia_maxima"]


def test_get_equipos_criticos_cachea_por_request_con_misma_clave(app, factory):
    zona = factory.zona()
    _equipo_vencido(factory, zona=zona)

    with app.test_request_context("/"):
        r1 = get_equipos_criticos(zona_id=zona.id)
        r2 = get_equipos_criticos(zona_id=zona.id)
        assert r1 is r2


# ---------------------------------------------------------------------------
# get_resumen_global / invalidar_cache_resumen_global
# ---------------------------------------------------------------------------

def test_get_resumen_global_cuenta_vencidos_y_proximos(app, factory):
    invalidar_cache_resumen_global()
    _equipo_vencido(factory)

    with app.test_request_context("/"):
        resumen = get_resumen_global(force_refresh=True)

    assert resumen["vencidos"] == 1
    assert resumen["proximos"] == 0
    assert resumen["total"] == 1


def test_get_resumen_global_usa_cache_entre_llamadas(app, factory):
    invalidar_cache_resumen_global()
    _equipo_vencido(factory)

    with app.test_request_context("/"):
        primero = get_resumen_global(force_refresh=True)

    _equipo_vencido(factory)

    with app.test_request_context("/"):
        segundo = get_resumen_global()

    assert segundo == primero
    assert segundo["total"] == 1


def test_invalidar_cache_resumen_global_fuerza_recalculo(app, factory):
    from flask import g

    invalidar_cache_resumen_global()
    _equipo_vencido(factory)

    with app.test_request_context("/"):
        primero = get_resumen_global(force_refresh=True)

    invalidar_cache_resumen_global()
    _equipo_vencido(factory)
    # g._equipos_criticos_cache es una caché por-request real: en producción cada
    # request HTTP la recibe vacía. Aquí ambos test_request_context comparten el
    # app_context de la fixture `app`, así que se limpia a mano para simular el
    # aislamiento real entre requests.
    g.pop("_equipos_criticos_cache", None)

    with app.test_request_context("/"):
        segundo = get_resumen_global()

    assert segundo["total"] == 2
    assert segundo["total"] != primero["total"]
