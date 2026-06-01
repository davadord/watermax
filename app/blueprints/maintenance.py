from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from app import db
from app.models.maintenance import Mantenimiento, DetalleMantenimiento
from app.models.equipment import EquipoInstalado
from app.models.client import Cliente
from app.models.user import Usuario
from app.services.prediction_service import calcular_proximo_componente
from app.utils.decorators import role_required

maintenance_bp = Blueprint("maintenance", __name__)

_all_roles = ("propietario", "administrativo", "tecnico")
_admin_roles = ("propietario", "administrativo")


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


@maintenance_bp.route("/cliente/<int:cliente_id>")
@login_required
@role_required(*_all_roles)
def historial_cliente(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    equipos = (
        db.session.execute(
            select(EquipoInstalado)
            .where(EquipoInstalado.cliente_id == cliente_id)
            .options(
                joinedload(EquipoInstalado.tipo_equipo),
                joinedload(EquipoInstalado.zona),
                joinedload(EquipoInstalado.mantenimientos)
                .selectinload(Mantenimiento.detalles)
                .selectinload(DetalleMantenimiento.componente),
                joinedload(EquipoInstalado.mantenimientos)
                .selectinload(Mantenimiento.tecnico),
            )
        )
        .unique()
        .scalars()
        .all()
    )
    hoy = date.today()
    return render_template(
        "maintenance/cliente.html",
        cliente=cliente,
        equipos=equipos,
        hoy=hoy,
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


@maintenance_bp.route("/listado")
@login_required
@role_required(*_admin_roles)
def listado_mantenimientos():
    cliente_id = request.args.get("cliente_id", type=int)
    fecha_desde = request.args.get("fecha_desde", "")
    fecha_hasta = request.args.get("fecha_hasta", "")
    page = request.args.get("page", 1, type=int)

    clientes = db.session.execute(
        select(Cliente).order_by(Cliente.nombre)
    ).scalars().all()

    stmt = (
        select(Mantenimiento)
        .options(
            joinedload(Mantenimiento.tecnico),
            selectinload(Mantenimiento.detalles).selectinload(DetalleMantenimiento.componente),
        )
        .order_by(Mantenimiento.fecha.desc(), Mantenimiento.id.desc())
    )

    if cliente_id:
        stmt = stmt.where(
            Mantenimiento.equipo_id.in_(
                select(EquipoInstalado.id).where(EquipoInstalado.cliente_id == cliente_id)
            )
        )
    if fecha_desde:
        try:
            stmt = stmt.where(Mantenimiento.fecha >= date.fromisoformat(fecha_desde))
        except ValueError:
            pass
    if fecha_hasta:
        try:
            stmt = stmt.where(Mantenimiento.fecha <= date.fromisoformat(fecha_hasta))
        except ValueError:
            pass

    paginacion = db.paginate(stmt, page=page, per_page=30, error_out=False)

    return render_template(
        "maintenance/listado.html",
        paginacion=paginacion,
        clientes=clientes,
        cliente_id=cliente_id,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@maintenance_bp.route("/<int:mant_id>/editar", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def editar_mantenimiento(mant_id):
    mant = db.get_or_404(Mantenimiento, mant_id)

    if mant.motivo_anulacion:
        flash("No se puede editar un mantenimiento anulado.", "warning")
        return redirect(url_for("maintenance.listado_mantenimientos"))

    equipo = mant.equipo
    componentes = [tc.componente for tc in equipo.tipo_equipo.componentes]
    detalles_map = {d.componente_id: d for d in mant.detalles}

    tecnicos = db.session.execute(
        select(Usuario).where(Usuario.activo == True).order_by(Usuario.nombre)
    ).scalars().all()

    if request.method == "POST":
        fecha_str = request.form.get("fecha")
        try:
            fecha = date.fromisoformat(fecha_str)
        except (TypeError, ValueError):
            flash("Fecha inválida.", "danger")
            return render_template(
                "maintenance/editar.html",
                mant=mant, equipo=equipo, componentes=componentes,
                detalles_map=detalles_map, tecnicos=tecnicos, hoy=date.today(),
            )

        tecnico_id = request.form.get("tecnico_id", type=int) or mant.tecnico_id

        nuevos_detalles = []
        for comp in componentes:
            accion = request.form.get(f"accion_{comp.id}")
            if not accion:
                continue
            proximo = None
            if accion == "reemplazo":
                proximo = calcular_proximo_componente(equipo, comp, fecha)
            nuevos_detalles.append(DetalleMantenimiento(
                mantenimiento_id=mant.id,
                componente_id=comp.id,
                accion=accion,
                notas=request.form.get(f"notas_{comp.id}") or None,
                proximo_mantenimiento=proximo,
            ))

        if not nuevos_detalles:
            flash("Debe registrar al menos un componente.", "danger")
            return render_template(
                "maintenance/editar.html",
                mant=mant, equipo=equipo, componentes=componentes,
                detalles_map=detalles_map, tecnicos=tecnicos, hoy=date.today(),
            )

        try:
            mant.fecha = fecha
            mant.tecnico_id = tecnico_id
            mant.observaciones = request.form.get("observaciones") or None

            for d in list(mant.detalles):
                db.session.delete(d)
            db.session.flush()

            for d in nuevos_detalles:
                db.session.add(d)

            db.session.commit()
            flash("Mantenimiento actualizado correctamente.", "success")
            return redirect(url_for("maintenance.listado_mantenimientos"))

        except Exception:
            db.session.rollback()
            flash("Error al guardar. Intente nuevamente.", "danger")
            return render_template(
                "maintenance/editar.html",
                mant=mant, equipo=equipo, componentes=componentes,
                detalles_map=detalles_map, tecnicos=tecnicos, hoy=date.today(),
            )

    return render_template(
        "maintenance/editar.html",
        mant=mant,
        equipo=equipo,
        componentes=componentes,
        detalles_map=detalles_map,
        tecnicos=tecnicos,
        hoy=date.today(),
    )


@maintenance_bp.route("/<int:mant_id>/anular", methods=["POST"])
@login_required
@role_required(*_admin_roles)
def anular_mantenimiento(mant_id):
    mant = db.get_or_404(Mantenimiento, mant_id)

    if mant.motivo_anulacion:
        flash("Este mantenimiento ya está anulado.", "warning")
        return redirect(url_for("maintenance.listado_mantenimientos"))

    motivo = request.form.get("motivo", "").strip()
    if not motivo:
        flash("Debe indicar el motivo de anulación.", "danger")
        return redirect(url_for("maintenance.listado_mantenimientos"))

    mant.motivo_anulacion = motivo
    db.session.commit()
    flash("Mantenimiento anulado correctamente.", "success")
    return redirect(url_for("maintenance.listado_mantenimientos"))
