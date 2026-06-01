from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app import db
from app.models.client import Zona, Cliente
from app.models.equipment import EquipoInstalado, TipoEquipo, TipoEquipoComponente
from app.models.maintenance import Mantenimiento, DetalleMantenimiento
from app.services.prediction_service import (
    calcular_vencimientos, URGENCIA_VENCIDO, URGENCIA_PROXIMO,
)


def get_reporte_zona(zona_id: int, fecha=None) -> dict:
    zona = db.session.get(Zona, zona_id)

    stmt = (
        select(EquipoInstalado)
        .where(
            EquipoInstalado.zona_id == zona_id,
            EquipoInstalado.activo == True,
        )
        .options(
            joinedload(EquipoInstalado.cliente),
            joinedload(EquipoInstalado.tipo_equipo)
                .joinedload(TipoEquipo.componentes)
                .joinedload(TipoEquipoComponente.componente),
        )
        .order_by(EquipoInstalado.id)
    )
    equipos = db.session.execute(stmt).scalars().unique().all()

    fecha_ref = fecha or date.today()
    items = []
    resumen = {"total": 0, "vencidos": 0, "proximos": 0, "en_plazo": 0}

    for equipo in equipos:
        vencimientos = calcular_vencimientos(equipo, fecha_ref=fecha_ref)
        n_vencidos = sum(1 for v in vencimientos if v["urgencia"] == URGENCIA_VENCIDO)
        n_proximos = sum(1 for v in vencimientos if v["urgencia"] == URGENCIA_PROXIMO)

        resumen["total"] += 1
        if n_vencidos:
            resumen["vencidos"] += 1
        elif n_proximos:
            resumen["proximos"] += 1
        else:
            resumen["en_plazo"] += 1

        items.append({
            "equipo": equipo,
            "vencimientos": vencimientos,
            "n_vencidos": n_vencidos,
            "n_proximos": n_proximos,
        })

    items.sort(key=lambda x: (-x["n_vencidos"], -x["n_proximos"]))

    return {
        "zona": zona,
        "items": items,
        "resumen": resumen,
        "fecha_ref": fecha_ref,
        "fecha_generacion": date.today(),
    }


def get_reporte_cliente(cliente_id: int) -> dict:
    cliente = db.session.get(Cliente, cliente_id)

    stmt = (
        select(EquipoInstalado)
        .where(
            EquipoInstalado.cliente_id == cliente_id,
            EquipoInstalado.activo == True,
        )
        .options(
            joinedload(EquipoInstalado.zona),
            joinedload(EquipoInstalado.tipo_equipo)
                .joinedload(TipoEquipo.componentes)
                .joinedload(TipoEquipoComponente.componente),
        )
    )
    equipos = db.session.execute(stmt).scalars().unique().all()

    items = []
    for equipo in equipos:
        hist_stmt = (
            select(Mantenimiento)
            .where(
                Mantenimiento.equipo_id == equipo.id,
                Mantenimiento.completado == True,
                Mantenimiento.motivo_anulacion == None,
            )
            .options(
                joinedload(Mantenimiento.detalles)
                    .joinedload(DetalleMantenimiento.componente),
                joinedload(Mantenimiento.tecnico),
            )
            .order_by(Mantenimiento.fecha.desc())
        )
        historial = db.session.execute(hist_stmt).scalars().unique().all()

        items.append({
            "equipo": equipo,
            "historial": historial,
            "proyeccion": calcular_vencimientos(equipo),
        })

    return {
        "cliente": cliente,
        "items": items,
        "fecha_generacion": date.today(),
    }
