from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date

from app import db
from app.models.maintenance import Mantenimiento, DetalleMantenimiento
from app.models.equipment import EquipoInstalado, Componente
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
        mant = Mantenimiento(
            equipo_id=equipo.id,
            tecnico_id=current_user.id,
            fecha=date.today(),
            observaciones=request.form.get("observaciones"),
            completado=True,
        )
        db.session.add(mant)
        db.session.flush()

        for comp in componentes:
            accion = request.form.get(f"accion_{comp.id}")
            if accion:
                detalle = DetalleMantenimiento(
                    mantenimiento_id=mant.id,
                    componente_id=comp.id,
                    accion=accion,
                    notas=request.form.get(f"notas_{comp.id}"),
                )
                db.session.add(detalle)

        db.session.commit()
        flash("Mantenimiento registrado correctamente.", "success")
        return redirect(url_for("reports.dashboard"))

    return render_template(
        "maintenance/form.html", equipo=equipo, componentes=componentes
    )
