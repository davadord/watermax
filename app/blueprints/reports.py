from flask import Blueprint, render_template, request, Response, abort, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import select

from datetime import date, timedelta
from app import db
from app.models.client import Zona, Cliente
from app.models.equipment import EquipoInstalado
from app.services.prediction_service import (
    calcular_vencimientos, get_equipos_criticos, get_resumen_global,
    URGENCIA_VENCIDO, URGENCIA_PROXIMO,
)
from app.services.report_service import (
    get_reporte_zona, get_reporte_cliente, build_reporte_zona_pdf,
    get_reporte_componentes_cambiados, ESTADOS_POR_FILTRO,
)
from app.utils.decorators import role_required

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/dashboard")
@login_required
def dashboard():
    zona_id = request.args.get("zona_id", type=int)
    estado = request.args.get("estado", "")
    fecha_str = request.args.get("fecha")
    try:
        fecha_ref = date.fromisoformat(fecha_str) if fecha_str else date.today()
    except ValueError:
        fecha_ref = date.today()
    zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()

    mantenimientos_hoy = []
    if zona_id:
        equipos = db.session.execute(
            select(EquipoInstalado).where(
                EquipoInstalado.zona_id == zona_id, EquipoInstalado.activo == True
            )
        ).scalars().all()
        urgencias_filtro = ESTADOS_POR_FILTRO.get(estado)
        for equipo in equipos:
            vencimientos = calcular_vencimientos(equipo, fecha_ref=fecha_ref)
            if urgencias_filtro is not None:
                vencimientos = [v for v in vencimientos if v["urgencia"] in urgencias_filtro]
                if not vencimientos:
                    continue
            n_vencidos = sum(1 for v in vencimientos if v["urgencia"] == URGENCIA_VENCIDO)
            n_proximos = sum(1 for v in vencimientos if v["urgencia"] == URGENCIA_PROXIMO)
            mantenimientos_hoy.append({
                "equipo": equipo,
                "vencimientos": vencimientos,
                "_sort": (-n_vencidos, -n_proximos),
            })
        mantenimientos_hoy.sort(key=lambda x: x["_sort"])

    resumen_global = get_resumen_global()

    return render_template(
        "reports/dashboard.html",
        zonas=zonas,
        zona_id=zona_id,
        estado=estado,
        fecha=fecha_ref.isoformat(),
        mantenimientos_hoy=mantenimientos_hoy,
        resumen_global=resumen_global,
        today=date.today().isoformat(),
    )


@reports_bp.route("/criticos")
@login_required
def criticos():
    zona_id = request.args.get("zona_id", type=int)
    urgencia = request.args.get("urgencia")
    cliente_id = request.args.get("cliente_id", type=int)
    zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()
    clientes = db.session.execute(
        select(Cliente).where(Cliente.activo == True).order_by(Cliente.nombre)
    ).scalars().all()
    equipos_criticos = get_equipos_criticos(zona_id=zona_id, urgencia=urgencia, cliente_id=cliente_id)

    return render_template(
        "reports/criticos.html",
        equipos_criticos=equipos_criticos,
        zonas=zonas,
        zona_id=zona_id,
        urgencia=urgencia,
        clientes=clientes,
        cliente_id=cliente_id,
    )


@reports_bp.route("/componentes-cambiados")
@login_required
@role_required("propietario", "administrativo")
def componentes_cambiados():
    hasta_str = request.args.get("hasta")
    desde_str = request.args.get("desde")
    try:
        hasta = date.fromisoformat(hasta_str) if hasta_str else date.today()
    except ValueError:
        hasta = date.today()
    try:
        desde = date.fromisoformat(desde_str) if desde_str else hasta - timedelta(days=90)
    except ValueError:
        desde = hasta - timedelta(days=90)

    zona_id = request.args.get("zona_id", type=int)
    cliente_id = request.args.get("cliente_id", type=int)

    zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()
    clientes = db.session.execute(
        select(Cliente).where(Cliente.activo == True).order_by(Cliente.nombre)
    ).scalars().all()

    datos = get_reporte_componentes_cambiados(
        desde, hasta, zona_id=zona_id, cliente_id=cliente_id
    )

    return render_template(
        "reports/componentes_cambiados.html",
        **datos,
        zonas=zonas,
        clientes=clientes,
    )


@reports_bp.route("/zona/<int:zona_id>/pdf")
@login_required
def pdf_zona(zona_id):
    from datetime import date as date_type
    fecha_str = request.args.get("fecha")
    try:
        fecha = date_type.fromisoformat(fecha_str) if fecha_str else None
    except ValueError:
        fecha = None
    estado = request.args.get("estado") or None
    datos = get_reporte_zona(zona_id, fecha=fecha, estado=estado)
    if not datos["zona"]:
        abort(404)
    try:
        pdf = build_reporte_zona_pdf(datos)
    except Exception:
        abort(503)
    slug = datos["zona"].nombre.lower().replace(" ", "-")
    fecha_nombre = datos["fecha_ref"].strftime("%Y-%m-%d")
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=reporte-zona-{slug}-{fecha_nombre}.pdf",
            "Cache-Control": "no-store",
        },
    )


@reports_bp.route("/cliente/<int:cliente_id>")
@login_required
def configurar_reporte_cliente(cliente_id):
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(404)
    equipos = db.session.execute(
        select(EquipoInstalado)
        .where(EquipoInstalado.cliente_id == cliente_id, EquipoInstalado.activo == True)
        .order_by(EquipoInstalado.id)
    ).scalars().all()
    return render_template(
        "reports/configurar_cliente.html",
        cliente=cliente, equipos=equipos, hoy=date.today().isoformat(),
    )


@reports_bp.route("/cliente/<int:cliente_id>/pdf")
@login_required
def pdf_cliente(cliente_id):
    from weasyprint import HTML
    equipo_id = request.args.get("equipo_id", type=int)
    desde_str = request.args.get("desde")
    hasta_str = request.args.get("hasta")
    try:
        desde = date.fromisoformat(desde_str) if desde_str else None
    except ValueError:
        desde = None
    try:
        hasta = date.fromisoformat(hasta_str) if hasta_str else None
    except ValueError:
        hasta = None

    datos = get_reporte_cliente(cliente_id, equipo_id=equipo_id, desde=desde, hasta=hasta)
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
        headers={
            "Content-Disposition": f"inline; filename=reporte-cliente-{slug}.pdf",
            "Cache-Control": "no-store",
        },
    )
