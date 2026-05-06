from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import db
from app.models.maintenance import Mantenimiento, DetalleMantenimiento
from app.models.equipment import EquipoInstalado
from app.services.prediction_service import calcular_proximo_componente
from app.utils.decorators import role_required

maintenance_bp = Blueprint("maintenance", __name__)

_all_roles = ("propietario", "administrativo", "tecnico")


@maintenance_bp.route("/nuevo/<int:equipo_id>", methods=["GET", "POST"])
@login_required
@role_required(*_all_roles)
def nuevo_mantenimiento(equipo_id):
    equipo = db.get_or_404(EquipoInstalado, equipo_id)
    componentes = [tc.componente for tc in equipo.tipo_equipo.componentes]

    if request.method == "POST":
        fecha_str = request.form.get("fecha")
        try:
            fecha = date.fromisoformat(fecha_str)
        except (TypeError, ValueError):
            flash("Fecha inválida.", "danger")
            return render_template("maintenance/form.html", equipo=equipo, componentes=componentes, hoy=date.today())

        try:
            mant = Mantenimiento(
                equipo_id=equipo.id,
                tecnico_id=current_user.id,
                fecha=fecha,
                observaciones=request.form.get("observaciones") or None,
                completado=True,
            )
            db.session.add(mant)
            db.session.flush()

            detalles = []
            for comp in componentes:
                accion = request.form.get(f"accion_{comp.id}")
                if not accion:
                    continue
                proximo = None
                if accion == "reemplazo":
                    proximo = calcular_proximo_componente(equipo, comp, fecha)
                detalles.append(DetalleMantenimiento(
                    mantenimiento_id=mant.id,
                    componente_id=comp.id,
                    accion=accion,
                    notas=request.form.get(f"notas_{comp.id}") or None,
                    proximo_mantenimiento=proximo,
                ))

            if not detalles:
                db.session.rollback()
                flash("Debe registrar al menos un componente.", "danger")
                return render_template("maintenance/form.html", equipo=equipo, componentes=componentes, hoy=date.today())

            for d in detalles:
                db.session.add(d)
            db.session.commit()
            flash("Mantenimiento registrado correctamente.", "success")
            return redirect(url_for("maintenance.historial_equipo", equipo_id=equipo.id))

        except Exception:
            db.session.rollback()
            flash("Error al guardar. Intente nuevamente.", "danger")
            return render_template("maintenance/form.html", equipo=equipo, componentes=componentes, hoy=date.today())

    return render_template(
        "maintenance/form.html",
        equipo=equipo,
        componentes=componentes,
        hoy=date.today(),
    )


@maintenance_bp.route("/equipo/<int:equipo_id>")
@login_required
@role_required(*_all_roles)
def historial_equipo(equipo_id):
    equipo = db.get_or_404(EquipoInstalado, equipo_id)
    page = request.args.get("page", 1, type=int)
    stmt = (
        select(Mantenimiento)
        .where(Mantenimiento.equipo_id == equipo_id)
        .order_by(Mantenimiento.fecha.desc())
        .options(
            selectinload(Mantenimiento.detalles).selectinload(DetalleMantenimiento.componente),
            selectinload(Mantenimiento.tecnico),
        )
    )
    paginacion = db.paginate(stmt, page=page, per_page=20, error_out=False)
    return render_template("maintenance/equipo.html", equipo=equipo, paginacion=paginacion)
