from flask import Blueprint, render_template, request
from flask_login import login_required

from app.models.client import Zona
from app.models.equipment import EquipoInstalado
from app.services.prediction_service import calcular_vencimientos

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
            mantenimientos_hoy.append({"equipo": equipo, "vencimientos": vencimientos})

    return render_template(
        "reports/dashboard.html",
        zonas=zonas,
        zona_id=zona_id,
        mantenimientos_hoy=mantenimientos_hoy,
    )
