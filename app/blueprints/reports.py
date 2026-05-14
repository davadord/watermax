from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models.client import Zona
from app.models.equipment import EquipoInstalado
from app.services.prediction_service import (
    calcular_vencimientos, get_equipos_criticos,
    URGENCIA_VENCIDO, URGENCIA_PROXIMO,
)

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/dashboard")
@login_required
def dashboard():
    zona_id = request.args.get("zona_id", type=int)
    zonas = Zona.query.order_by(Zona.nombre).all()

    mantenimientos_hoy = []
    if zona_id:
        equipos = EquipoInstalado.query.filter_by(zona_id=zona_id, activo=True).all()
        for equipo in equipos:
            vencimientos = calcular_vencimientos(equipo)
            n_vencidos = sum(1 for v in vencimientos if v["urgencia"] == URGENCIA_VENCIDO)
            n_proximos = sum(1 for v in vencimientos if v["urgencia"] == URGENCIA_PROXIMO)
            mantenimientos_hoy.append({
                "equipo": equipo,
                "vencimientos": vencimientos,
                "_sort": (-n_vencidos, -n_proximos),
            })
        mantenimientos_hoy.sort(key=lambda x: x["_sort"])

    # Resumen global para el estado sin zona seleccionada (#23)
    criticos_global = get_equipos_criticos()
    resumen_global = {
        "vencidos": sum(1 for i in criticos_global if i["urgencia_maxima"] == URGENCIA_VENCIDO),
        "proximos": sum(1 for i in criticos_global if i["urgencia_maxima"] == URGENCIA_PROXIMO),
        "total": len(criticos_global),
    }

    return render_template(
        "reports/dashboard.html",
        zonas=zonas,
        zona_id=zona_id,
        mantenimientos_hoy=mantenimientos_hoy,
        resumen_global=resumen_global,
    )


@reports_bp.route("/criticos")
@login_required
def criticos():
    zona_id = request.args.get("zona_id", type=int)
    urgencia = request.args.get("urgencia")
    zonas = Zona.query.order_by(Zona.nombre).all()
    equipos_criticos = get_equipos_criticos(zona_id=zona_id, urgencia=urgencia)

    return render_template(
        "reports/criticos.html",
        equipos_criticos=equipos_criticos,
        zonas=zonas,
        zona_id=zona_id,
        urgencia=urgencia,
    )
