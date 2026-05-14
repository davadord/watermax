from flask import Blueprint, render_template, request, Response, abort, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import select

from datetime import date
from app import db
from app.models.client import Zona
from app.models.equipment import EquipoInstalado
from app.services.prediction_service import (
    calcular_vencimientos, get_equipos_criticos,
    URGENCIA_VENCIDO, URGENCIA_PROXIMO,
)
from app.services.report_service import get_reporte_zona, get_reporte_cliente

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/dashboard")
@login_required
def dashboard():
    zona_id = request.args.get("zona_id", type=int)
    zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()

    mantenimientos_hoy = []
    if zona_id:
        equipos = db.session.execute(
            select(EquipoInstalado).where(
                EquipoInstalado.zona_id == zona_id, EquipoInstalado.activo == True
            )
        ).scalars().all()
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
        today=date.today().isoformat(),
    )


@reports_bp.route("/criticos")
@login_required
def criticos():
    zona_id = request.args.get("zona_id", type=int)
    urgencia = request.args.get("urgencia")
    zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()
    equipos_criticos = get_equipos_criticos(zona_id=zona_id, urgencia=urgencia)

    return render_template(
        "reports/criticos.html",
        equipos_criticos=equipos_criticos,
        zonas=zonas,
        zona_id=zona_id,
        urgencia=urgencia,
    )


@reports_bp.route("/zona/<int:zona_id>/pdf")
@login_required
def pdf_zona(zona_id):
    from weasyprint import HTML
    from datetime import date as date_type
    fecha_str = request.args.get("fecha")
    try:
        fecha = date_type.fromisoformat(fecha_str) if fecha_str else None
    except ValueError:
        fecha = None
    datos = get_reporte_zona(zona_id, fecha=fecha)
    if not datos["zona"]:
        abort(404)
    html = render_template("reports/pdf_zona.html", **datos)
    try:
        pdf = HTML(string=html).write_pdf()
    except Exception:
        abort(503)
    slug = datos["zona"].nombre.lower().replace(" ", "-")
    fecha_nombre = datos["fecha_ref"].strftime("%Y-%m-%d")
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=reporte-zona-{slug}-{fecha_nombre}.pdf"},
    )


@reports_bp.route("/cliente/<int:cliente_id>/pdf")
@login_required
def pdf_cliente(cliente_id):
    from weasyprint import HTML
    datos = get_reporte_cliente(cliente_id)
    if not datos["cliente"]:
        abort(404)
    html = render_template("reports/pdf_cliente.html", **datos)
    try:
        pdf = HTML(string=html).write_pdf()
    except Exception:
        abort(503)
    slug = datos["cliente"].nombre.lower().replace(" ", "-")
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename=reporte-cliente-{slug}.pdf"},
    )
