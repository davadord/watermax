from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app import db
from app.models.client import Cliente, Zona
from app.models.equipment import TipoEquipo, Componente, TipoEquipoComponente, EquipoInstalado

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/clientes")
@login_required
def clientes():
    clientes = Cliente.query.filter_by(activo=True).order_by(Cliente.nombre).all()
    return render_template("admin/clientes.html", clientes=clientes)


@admin_bp.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
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


@admin_bp.route("/zonas")
@login_required
def zonas():
    zonas = Zona.query.order_by(Zona.nombre).all()
    return render_template("admin/zonas.html", zonas=zonas)


@admin_bp.route("/equipos")
@login_required
def equipos():
    equipos = EquipoInstalado.query.filter_by(activo=True).all()
    return render_template("admin/equipos.html", equipos=equipos)
