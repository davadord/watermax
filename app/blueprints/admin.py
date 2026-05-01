from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app import db
from app.models.client import Cliente, Zona
from app.models.equipment import TipoEquipo, EquipoInstalado
from app.utils.decorators import role_required

admin_bp = Blueprint("admin", __name__)

_admin_roles = ("propietario", "administrativo")


# ── Clientes ──────────────────────────────────────────────────────────────────

@admin_bp.route("/clientes")
@login_required
@role_required(*_admin_roles)
def clientes():
    zona_id = request.args.get("zona_id", type=int)
    query = Cliente.query.filter_by(activo=True)
    if zona_id:
        query = query.filter_by(zona_id=zona_id)
    clientes = query.order_by(Cliente.nombre).all()
    zonas = Zona.query.order_by(Zona.nombre).all()
    return render_template("admin/clientes.html", clientes=clientes, zonas=zonas, zona_id=zona_id)


@admin_bp.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def nuevo_cliente():
    zonas = Zona.query.order_by(Zona.nombre).all()
    if request.method == "POST":
        zona_id = request.form.get("zona_id")
        if not zona_id:
            flash("Debes seleccionar una zona.", "danger")
            return render_template("admin/cliente_form.html", zonas=zonas, cliente=None)
        cliente = Cliente(
            nombre=request.form["nombre"],
            telefono=request.form.get("telefono"),
            direccion=request.form.get("direccion"),
            email=request.form.get("email"),
            zona_id=int(zona_id),
        )
        db.session.add(cliente)
        db.session.commit()
        flash(f"Cliente {cliente.nombre} registrado.", "success")
        return redirect(url_for("admin.clientes"))
    return render_template("admin/cliente_form.html", zonas=zonas, cliente=None)


@admin_bp.route("/clientes/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def editar_cliente(id):
    cliente = db.session.get(Cliente, id)
    if not cliente or not cliente.activo:
        flash("Cliente no encontrado.", "danger")
        return redirect(url_for("admin.clientes"))
    zonas = Zona.query.order_by(Zona.nombre).all()
    if request.method == "POST":
        zona_id = request.form.get("zona_id")
        if not zona_id:
            flash("Debes seleccionar una zona.", "danger")
            return render_template("admin/cliente_form.html", zonas=zonas, cliente=cliente)
        cliente.nombre = request.form["nombre"]
        cliente.telefono = request.form.get("telefono")
        cliente.direccion = request.form.get("direccion")
        cliente.email = request.form.get("email")
        cliente.zona_id = int(zona_id)
        db.session.commit()
        flash(f"Cliente {cliente.nombre} actualizado.", "success")
        return redirect(url_for("admin.clientes"))
    return render_template("admin/cliente_form.html", zonas=zonas, cliente=cliente)


@admin_bp.route("/clientes/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required(*_admin_roles)
def eliminar_cliente(id):
    cliente = db.session.get(Cliente, id)
    if not cliente or not cliente.activo:
        flash("Cliente no encontrado.", "danger")
        return redirect(url_for("admin.clientes"))
    equipos_activos = [e for e in cliente.equipos if e.activo]
    if equipos_activos:
        flash(f"No se puede eliminar: {cliente.nombre} tiene equipos instalados activos.", "danger")
        return redirect(url_for("admin.clientes"))
    cliente.activo = False
    db.session.commit()
    flash(f"Cliente {cliente.nombre} eliminado.", "success")
    return redirect(url_for("admin.clientes"))


# ── Zonas ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/zonas")
@login_required
@role_required(*_admin_roles)
def zonas():
    zonas = Zona.query.order_by(Zona.nombre).all()
    return render_template("admin/zonas.html", zonas=zonas)


@admin_bp.route("/zonas/nueva", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def nueva_zona():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return render_template("admin/zona_form.html", zona=None)
        zona = Zona(nombre=nombre, descripcion=request.form.get("descripcion"))
        db.session.add(zona)
        db.session.commit()
        flash(f"Zona {zona.nombre} creada.", "success")
        return redirect(url_for("admin.zonas"))
    return render_template("admin/zona_form.html", zona=None)


@admin_bp.route("/zonas/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def editar_zona(id):
    zona = db.session.get(Zona, id)
    if not zona:
        flash("Zona no encontrada.", "danger")
        return redirect(url_for("admin.zonas"))
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return render_template("admin/zona_form.html", zona=zona)
        zona.nombre = nombre
        zona.descripcion = request.form.get("descripcion")
        db.session.commit()
        flash(f"Zona {zona.nombre} actualizada.", "success")
        return redirect(url_for("admin.zonas"))
    return render_template("admin/zona_form.html", zona=zona)


@admin_bp.route("/zonas/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required(*_admin_roles)
def eliminar_zona(id):
    zona = db.session.get(Zona, id)
    if not zona:
        flash("Zona no encontrada.", "danger")
        return redirect(url_for("admin.zonas"))
    clientes_activos = [c for c in zona.clientes if c.activo]
    if clientes_activos:
        flash(f"No se puede eliminar: la zona {zona.nombre} tiene clientes activos.", "danger")
        return redirect(url_for("admin.zonas"))
    db.session.delete(zona)
    db.session.commit()
    flash(f"Zona {zona.nombre} eliminada.", "success")
    return redirect(url_for("admin.zonas"))


# ── Equipos ───────────────────────────────────────────────────────────────────

@admin_bp.route("/equipos")
@login_required
@role_required(*_admin_roles)
def equipos():
    equipos = EquipoInstalado.query.filter_by(activo=True).all()
    return render_template("admin/equipos.html", equipos=equipos)


@admin_bp.route("/equipos/nuevo", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def nuevo_equipo():
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre).all()
    tipos_equipo = TipoEquipo.query.order_by(TipoEquipo.nombre).all()
    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        tipo_equipo_id = request.form.get("tipo_equipo_id")
        fecha_str = request.form.get("fecha_instalacion")
        if not cliente_id or not tipo_equipo_id or not fecha_str:
            flash("Cliente, tipo de equipo y fecha son obligatorios.", "danger")
            return render_template("admin/equipo_form.html", clientes=clientes, tipos_equipo=tipos_equipo, equipo=None)
        equipo = EquipoInstalado(
            cliente_id=int(cliente_id),
            tipo_equipo_id=int(tipo_equipo_id),
            numero_serie=request.form.get("numero_serie"),
            fecha_instalacion=date.fromisoformat(fecha_str),
        )
        db.session.add(equipo)
        db.session.commit()
        flash("Equipo registrado.", "success")
        return redirect(url_for("admin.equipos"))
    return render_template("admin/equipo_form.html", clientes=clientes, tipos_equipo=tipos_equipo, equipo=None)


@admin_bp.route("/equipos/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def editar_equipo(id):
    equipo = db.session.get(EquipoInstalado, id)
    if not equipo or not equipo.activo:
        flash("Equipo no encontrado.", "danger")
        return redirect(url_for("admin.equipos"))
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre).all()
    tipos_equipo = TipoEquipo.query.order_by(TipoEquipo.nombre).all()
    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        tipo_equipo_id = request.form.get("tipo_equipo_id")
        fecha_str = request.form.get("fecha_instalacion")
        if not cliente_id or not tipo_equipo_id or not fecha_str:
            flash("Cliente, tipo de equipo y fecha son obligatorios.", "danger")
            return render_template("admin/equipo_form.html", clientes=clientes, tipos_equipo=tipos_equipo, equipo=equipo)
        equipo.cliente_id = int(cliente_id)
        equipo.tipo_equipo_id = int(tipo_equipo_id)
        equipo.numero_serie = request.form.get("numero_serie")
        equipo.fecha_instalacion = date.fromisoformat(fecha_str)
        db.session.commit()
        flash("Equipo actualizado.", "success")
        return redirect(url_for("admin.equipos"))
    return render_template("admin/equipo_form.html", clientes=clientes, tipos_equipo=tipos_equipo, equipo=equipo)


@admin_bp.route("/equipos/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required(*_admin_roles)
def eliminar_equipo(id):
    equipo = db.session.get(EquipoInstalado, id)
    if not equipo or not equipo.activo:
        flash("Equipo no encontrado.", "danger")
        return redirect(url_for("admin.equipos"))
    equipo.activo = False
    db.session.commit()
    flash("Equipo eliminado.", "success")
    return redirect(url_for("admin.equipos"))
