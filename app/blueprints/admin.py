from datetime import date, datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import select, delete

from app import db
from app.models.client import Cliente, Zona, TIPOS_IDENTIFICADOR
from app.models.equipment import TipoEquipo, Componente, TipoEquipoComponente, EquipoInstalado
from app.models.user import Usuario
from app.services.prediction_service import invalidar_cache_resumen_global
from app.utils.decorators import role_required

admin_bp = Blueprint("admin", __name__)

_admin_roles = ("propietario", "administrativo")
_solo_propietario = ("propietario",)
ROLES_USUARIO = ("propietario", "administrativo", "tecnico")


# ── Clientes ──────────────────────────────────────────────────────────────────

@admin_bp.route("/clientes")
@login_required
@role_required(*_admin_roles)
def clientes():
    zona_id = request.args.get("zona_id", type=int)
    zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()
    stmt = select(Cliente).where(Cliente.activo == True)
    if zona_id:
        stmt = stmt.join(Cliente.equipos).where(
            EquipoInstalado.zona_id == zona_id, EquipoInstalado.activo == True
        )
    clientes = db.session.execute(stmt.order_by(Cliente.nombre)).scalars().all()
    return render_template("admin/clientes.html", clientes=clientes, zonas=zonas, zona_id=zona_id)


@admin_bp.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def nuevo_cliente():
    if request.method == "POST":
        error = _validar_identificador(
            request.form.get("tipo_identificador"),
            request.form.get("identificador", "").strip(),
            exclude_id=None,
        )
        if error:
            flash(error, "danger")
            return render_template("admin/cliente_form.html", cliente=None,
                                   tipos=TIPOS_IDENTIFICADOR)
        cliente = Cliente(
            nombre=request.form["nombre"],
            tipo_identificador=request.form["tipo_identificador"],
            identificador=request.form["identificador"].strip(),
            telefono=request.form.get("telefono"),
            direccion=request.form.get("direccion"),
            email=request.form.get("email"),
        )
        db.session.add(cliente)
        db.session.commit()
        flash(f"Cliente {cliente.nombre} registrado.", "success")
        return redirect(url_for("admin.clientes"))
    return render_template("admin/cliente_form.html", cliente=None, tipos=TIPOS_IDENTIFICADOR)


@admin_bp.route("/clientes/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def editar_cliente(id):
    cliente = db.session.get(Cliente, id)
    if not cliente or not cliente.activo:
        flash("Cliente no encontrado.", "danger")
        return redirect(url_for("admin.clientes"))
    if request.method == "POST":
        error = _validar_identificador(
            request.form.get("tipo_identificador"),
            request.form.get("identificador", "").strip(),
            exclude_id=cliente.id,
        )
        if error:
            flash(error, "danger")
            return render_template("admin/cliente_form.html", cliente=cliente,
                                   tipos=TIPOS_IDENTIFICADOR)
        cliente.nombre = request.form["nombre"]
        cliente.tipo_identificador = request.form["tipo_identificador"]
        cliente.identificador = request.form["identificador"].strip()
        cliente.telefono = request.form.get("telefono")
        cliente.direccion = request.form.get("direccion")
        cliente.email = request.form.get("email")
        db.session.commit()
        flash(f"Cliente {cliente.nombre} actualizado.", "success")
        return redirect(url_for("admin.clientes"))
    return render_template("admin/cliente_form.html", cliente=cliente, tipos=TIPOS_IDENTIFICADOR)


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


@admin_bp.route("/clientes/sugerir-codigo")
@login_required
def sugerir_codigo_otro():
    telefono = request.args.get("telefono", "")
    digitos = "".join(c for c in telefono if c.isdigit())
    sufijo = digitos[-4:] if len(digitos) >= 4 else digitos.zfill(4)
    hoy = datetime.now().strftime("%Y%m%d")
    return jsonify({"codigo": f"OTR-{sufijo}-{hoy}"})


def _validar_identificador(tipo, valor, exclude_id):
    if not tipo or not valor:
        return "El tipo y número de identificación son obligatorios."
    if tipo == "Cédula" and (not valor.isdigit() or len(valor) != 10):
        return "La cédula debe tener exactamente 10 dígitos numéricos."
    if tipo == "RUC" and (not valor.isdigit() or len(valor) != 13):
        return "El RUC debe tener exactamente 13 dígitos numéricos."
    stmt = select(Cliente).where(Cliente.identificador == valor)
    if exclude_id:
        stmt = stmt.where(Cliente.id != exclude_id)
    if db.session.execute(stmt).scalars().first():
        return f"Ya existe un cliente con el identificador {valor}."
    return None


# ── Zonas ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/zonas")
@login_required
@role_required(*_admin_roles)
def zonas():
    zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()
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
    equipos_activos = [e for e in zona.equipos if e.activo]
    if equipos_activos:
        flash(f"No se puede eliminar: la zona {zona.nombre} tiene equipos instalados activos.", "danger")
        return redirect(url_for("admin.zonas"))
    db.session.delete(zona)
    db.session.commit()
    flash(f"Zona {zona.nombre} eliminada.", "success")
    return redirect(url_for("admin.zonas"))


# ── Tipos de Equipo ───────────────────────────────────────────────────────────

@admin_bp.route("/tipos-equipo")
@login_required
@role_required(*_admin_roles)
def tipos_equipo():
    tipos = db.session.execute(select(TipoEquipo).order_by(TipoEquipo.nombre)).scalars().all()
    return render_template("admin/tipos_equipo.html", tipos=tipos)


@admin_bp.route("/tipos-equipo/nuevo", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def nuevo_tipo_equipo():
    componentes = db.session.execute(select(Componente).order_by(Componente.nombre)).scalars().all()
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return render_template("admin/tipo_equipo_form.html", tipo=None, componentes=componentes)
        tipo = TipoEquipo(
            nombre=nombre,
            marca=request.form.get("marca") or None,
            descripcion=request.form.get("descripcion") or None,
        )
        db.session.add(tipo)
        db.session.flush()
        _guardar_componentes(tipo, request.form, componentes)
        db.session.commit()
        flash(f"Tipo de equipo {tipo.nombre} creado.", "success")
        return redirect(url_for("admin.tipos_equipo"))
    return render_template("admin/tipo_equipo_form.html", tipo=None, componentes=componentes)


@admin_bp.route("/tipos-equipo/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def editar_tipo_equipo(id):
    tipo = db.session.get(TipoEquipo, id)
    if not tipo:
        flash("Tipo de equipo no encontrado.", "danger")
        return redirect(url_for("admin.tipos_equipo"))
    componentes = db.session.execute(select(Componente).order_by(Componente.nombre)).scalars().all()
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return render_template("admin/tipo_equipo_form.html", tipo=tipo, componentes=componentes)
        tipo.nombre = nombre
        tipo.marca = request.form.get("marca") or None
        tipo.descripcion = request.form.get("descripcion") or None
        db.session.execute(
            delete(TipoEquipoComponente).where(TipoEquipoComponente.tipo_equipo_id == tipo.id)
        )
        _guardar_componentes(tipo, request.form, componentes)
        db.session.commit()
        flash(f"Tipo de equipo {tipo.nombre} actualizado.", "success")
        return redirect(url_for("admin.tipos_equipo"))
    return render_template("admin/tipo_equipo_form.html", tipo=tipo, componentes=componentes)


@admin_bp.route("/tipos-equipo/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required(*_admin_roles)
def eliminar_tipo_equipo(id):
    tipo = db.session.get(TipoEquipo, id)
    if not tipo:
        flash("Tipo de equipo no encontrado.", "danger")
        return redirect(url_for("admin.tipos_equipo"))
    if tipo.equipos:
        flash(f"No se puede eliminar: {tipo.nombre} tiene equipos instalados asociados.", "danger")
        return redirect(url_for("admin.tipos_equipo"))
    db.session.delete(tipo)
    db.session.commit()
    flash(f"Tipo de equipo {tipo.nombre} eliminado.", "success")
    return redirect(url_for("admin.tipos_equipo"))


def _guardar_componentes(tipo, form, componentes):
    seleccionados = form.getlist("componente_ids")
    for comp in componentes:
        if str(comp.id) in seleccionados:
            db.session.add(TipoEquipoComponente(
                tipo_equipo_id=tipo.id,
                componente_id=comp.id,
            ))


# ── Componentes ───────────────────────────────────────────────────────────────

@admin_bp.route("/componentes")
@login_required
@role_required(*_admin_roles)
def componentes():
    comps = db.session.execute(select(Componente).order_by(Componente.nombre)).scalars().all()
    return render_template("admin/componentes.html", componentes=comps)


@admin_bp.route("/componentes/nuevo", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def nuevo_componente():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return render_template("admin/componente_form.html", componente=None)
        comp = Componente(
            nombre=nombre,
            descripcion=request.form.get("descripcion") or None,
            intervalo_nominal=int(request.form.get("intervalo_nominal")),
        )
        db.session.add(comp)
        db.session.commit()
        flash(f"Componente {comp.nombre} creado.", "success")
        return redirect(url_for("admin.componentes"))
    return render_template("admin/componente_form.html", componente=None)


@admin_bp.route("/componentes/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def editar_componente(id):
    comp = db.session.get(Componente, id)
    if not comp:
        flash("Componente no encontrado.", "danger")
        return redirect(url_for("admin.componentes"))
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre es obligatorio.", "danger")
            return render_template("admin/componente_form.html", componente=comp)
        comp.nombre = nombre
        comp.descripcion = request.form.get("descripcion") or None
        comp.intervalo_nominal = int(request.form.get("intervalo_nominal"))
        db.session.commit()
        flash(f"Componente {comp.nombre} actualizado.", "success")
        return redirect(url_for("admin.componentes"))
    return render_template("admin/componente_form.html", componente=comp)


@admin_bp.route("/componentes/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required(*_admin_roles)
def eliminar_componente(id):
    comp = db.session.get(Componente, id)
    if not comp:
        flash("Componente no encontrado.", "danger")
        return redirect(url_for("admin.componentes"))
    db.session.delete(comp)
    db.session.commit()
    flash(f"Componente {comp.nombre} eliminado.", "success")
    return redirect(url_for("admin.componentes"))


# ── Equipos ───────────────────────────────────────────────────────────────────

@admin_bp.route("/equipos")
@login_required
@role_required(*_admin_roles)
def equipos():
    zona_id = request.args.get("zona_id", type=int)
    cliente_id = request.args.get("cliente_id", type=int)

    stmt = select(EquipoInstalado).where(EquipoInstalado.activo == True)
    if zona_id:
        stmt = stmt.where(EquipoInstalado.zona_id == zona_id)
    if cliente_id:
        stmt = stmt.where(EquipoInstalado.cliente_id == cliente_id)
    equipos = db.session.execute(stmt).scalars().all()

    stmt_i = select(EquipoInstalado).where(EquipoInstalado.activo == False)
    if zona_id:
        stmt_i = stmt_i.where(EquipoInstalado.zona_id == zona_id)
    if cliente_id:
        stmt_i = stmt_i.where(EquipoInstalado.cliente_id == cliente_id)
    equipos_inactivos = db.session.execute(stmt_i).scalars().all()

    if zona_id:
        sub_clientes = (
            select(EquipoInstalado.cliente_id)
            .where(EquipoInstalado.zona_id == zona_id, EquipoInstalado.activo == True)
            .distinct()
        )
        clientes = db.session.execute(
            select(Cliente)
            .where(Cliente.id.in_(sub_clientes), Cliente.activo == True)
            .order_by(Cliente.nombre)
        ).scalars().all()
    else:
        clientes = db.session.execute(
            select(Cliente).where(Cliente.activo == True).order_by(Cliente.nombre)
        ).scalars().all()

    if cliente_id:
        sub_zonas = (
            select(EquipoInstalado.zona_id)
            .where(EquipoInstalado.cliente_id == cliente_id, EquipoInstalado.activo == True)
            .distinct()
        )
        zonas = db.session.execute(
            select(Zona).where(Zona.id.in_(sub_zonas)).order_by(Zona.nombre)
        ).scalars().all()
    else:
        zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()

    return render_template("admin/equipos.html",
                           equipos=equipos,
                           equipos_inactivos=equipos_inactivos,
                           zonas=zonas,
                           clientes=clientes,
                           zona_id=zona_id,
                           cliente_id=cliente_id)


@admin_bp.route("/equipos/nuevo", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def nuevo_equipo():
    clientes = db.session.execute(
        select(Cliente).where(Cliente.activo == True).order_by(Cliente.nombre)
    ).scalars().all()
    tipos_equipo = db.session.execute(select(TipoEquipo).order_by(TipoEquipo.nombre)).scalars().all()
    zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()

    cliente_id_param = request.args.get("cliente_id", type=int)
    cliente_preseleccionado = None
    if cliente_id_param:
        c = db.session.get(Cliente, cliente_id_param)
        if c and c.activo:
            cliente_preseleccionado = c

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        tipo_equipo_id = request.form.get("tipo_equipo_id")
        zona_id = request.form.get("zona_id")
        fecha_str = request.form.get("fecha_instalacion")
        if not cliente_id or not tipo_equipo_id or not zona_id or not fecha_str:
            flash("Cliente, zona, tipo de equipo y fecha son obligatorios.", "danger")
            return render_template("admin/equipo_form.html",
                                   clientes=clientes, tipos_equipo=tipos_equipo,
                                   zonas=zonas, equipo=None, today=date.today(),
                                   cliente_preseleccionado=cliente_preseleccionado)
        fecha_instalacion = date.fromisoformat(fecha_str)
        if fecha_instalacion > date.today():
            flash("La fecha de instalación no puede ser futura.", "danger")
            return render_template("admin/equipo_form.html",
                                   clientes=clientes, tipos_equipo=tipos_equipo,
                                   zonas=zonas, equipo=None, today=date.today(),
                                   cliente_preseleccionado=cliente_preseleccionado)
        equipo = EquipoInstalado(
            cliente_id=int(cliente_id),
            tipo_equipo_id=int(tipo_equipo_id),
            zona_id=int(zona_id),
            sector=request.form.get("sector") or None,
            numero_serie=request.form.get("numero_serie"),
            fecha_instalacion=fecha_instalacion,
        )
        db.session.add(equipo)
        db.session.commit()
        invalidar_cache_resumen_global()
        flash("Equipo registrado.", "success")
        return redirect(url_for("admin.equipos"))
    return render_template("admin/equipo_form.html",
                           clientes=clientes, tipos_equipo=tipos_equipo,
                           zonas=zonas, equipo=None, today=date.today(),
                           cliente_preseleccionado=cliente_preseleccionado)


@admin_bp.route("/equipos/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required(*_admin_roles)
def editar_equipo(id):
    equipo = db.session.get(EquipoInstalado, id)
    if not equipo or not equipo.activo:
        flash("Equipo no encontrado.", "danger")
        return redirect(url_for("admin.equipos"))
    clientes = db.session.execute(
        select(Cliente).where(Cliente.activo == True).order_by(Cliente.nombre)
    ).scalars().all()
    tipos_equipo = db.session.execute(select(TipoEquipo).order_by(TipoEquipo.nombre)).scalars().all()
    zonas = db.session.execute(select(Zona).order_by(Zona.nombre)).scalars().all()
    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        tipo_equipo_id = request.form.get("tipo_equipo_id")
        zona_id = request.form.get("zona_id")
        fecha_str = request.form.get("fecha_instalacion")
        if not cliente_id or not tipo_equipo_id or not zona_id or not fecha_str:
            flash("Cliente, zona, tipo de equipo y fecha son obligatorios.", "danger")
            return render_template("admin/equipo_form.html",
                                   clientes=clientes, tipos_equipo=tipos_equipo,
                                   zonas=zonas, equipo=equipo, today=date.today(),
                                   cliente_preseleccionado=None)
        fecha_instalacion = date.fromisoformat(fecha_str)
        if fecha_instalacion > date.today():
            flash("La fecha de instalación no puede ser futura.", "danger")
            return render_template("admin/equipo_form.html",
                                   clientes=clientes, tipos_equipo=tipos_equipo,
                                   zonas=zonas, equipo=equipo, today=date.today(),
                                   cliente_preseleccionado=None)
        equipo.cliente_id = int(cliente_id)
        equipo.tipo_equipo_id = int(tipo_equipo_id)
        equipo.zona_id = int(zona_id)
        equipo.sector = request.form.get("sector") or None
        equipo.numero_serie = request.form.get("numero_serie")
        equipo.fecha_instalacion = fecha_instalacion
        db.session.commit()
        invalidar_cache_resumen_global()
        flash("Equipo actualizado.", "success")
        return redirect(url_for("admin.equipos"))
    return render_template("admin/equipo_form.html",
                           clientes=clientes, tipos_equipo=tipos_equipo,
                           zonas=zonas, equipo=equipo, today=date.today(),
                           cliente_preseleccionado=None)


@admin_bp.route("/equipos/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required(*_admin_roles)
def eliminar_equipo(id):
    equipo = db.session.get(EquipoInstalado, id)
    if not equipo or not equipo.activo:
        flash("Equipo no encontrado.", "danger")
        return redirect(url_for("admin.equipos"))
    if equipo.mantenimientos:
        equipo.activo = False
        db.session.commit()
        flash("Equipo desactivado. El historial de mantenimientos se conserva.", "success")
    else:
        db.session.delete(equipo)
        db.session.commit()
        flash("Equipo eliminado.", "success")
    invalidar_cache_resumen_global()
    return redirect(url_for("admin.equipos"))


@admin_bp.route("/equipos/<int:id>/reactivar", methods=["POST"])
@login_required
@role_required(*_admin_roles)
def reactivar_equipo(id):
    equipo = db.session.get(EquipoInstalado, id)
    if not equipo or equipo.activo:
        flash("Equipo no encontrado o ya está activo.", "danger")
        return redirect(url_for("admin.equipos"))
    equipo.activo = True
    equipo.fecha_reactivacion = date.today()
    db.session.commit()
    invalidar_cache_resumen_global()
    flash(f"Equipo {equipo.numero_serie or equipo.tipo_equipo.nombre} reactivado. El motor predictivo usará esta fecha como punto de partida.", "success")
    return redirect(url_for("admin.equipos"))


# ── Usuarios ──────────────────────────────────────────────────────────────────

@admin_bp.route("/usuarios")
@login_required
@role_required(*_solo_propietario)
def listar_usuarios():
    usuarios = db.session.execute(
        select(Usuario).where(Usuario.activo == True).order_by(Usuario.nombre)
    ).scalars().all()
    return render_template("admin/usuarios.html", usuarios=usuarios)


@admin_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
@role_required(*_solo_propietario)
def nuevo_usuario():
    if request.method == "POST":
        error = _validar_usuario(request.form, exclude_id=None, es_creacion=True)
        if error:
            flash(error, "danger")
            return render_template("admin/usuario_form.html", usuario=None, roles=ROLES_USUARIO)
        usuario = Usuario(
            nombre=request.form["nombre"].strip(),
            email=request.form["email"].strip(),
            rol=request.form["rol"],
        )
        usuario.set_password(request.form["password"])
        db.session.add(usuario)
        db.session.commit()
        flash(f"Usuario {usuario.nombre} creado.", "success")
        return redirect(url_for("admin.listar_usuarios"))
    return render_template("admin/usuario_form.html", usuario=None, roles=ROLES_USUARIO)


@admin_bp.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@login_required
@role_required(*_solo_propietario)
def editar_usuario(id):
    usuario = db.session.get(Usuario, id)
    if not usuario or not usuario.activo:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("admin.listar_usuarios"))
    if request.method == "POST":
        error = _validar_usuario(request.form, exclude_id=usuario.id, es_creacion=False)
        if error:
            flash(error, "danger")
            return render_template("admin/usuario_form.html", usuario=usuario, roles=ROLES_USUARIO)
        usuario.nombre = request.form["nombre"].strip()
        usuario.email = request.form["email"].strip()
        usuario.rol = request.form["rol"]
        password = request.form.get("password", "")
        if password:
            usuario.set_password(password)
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
        db.session.commit()
        flash(f"Usuario {usuario.nombre} actualizado.", "success")
        return redirect(url_for("admin.listar_usuarios"))
    return render_template("admin/usuario_form.html", usuario=usuario, roles=ROLES_USUARIO)


@admin_bp.route("/usuarios/<int:id>/eliminar", methods=["POST"])
@login_required
@role_required(*_solo_propietario)
def eliminar_usuario(id):
    usuario = db.session.get(Usuario, id)
    if not usuario or not usuario.activo:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for("admin.listar_usuarios"))
    if usuario.id == current_user.id:
        flash("No puedes desactivar tu propia cuenta.", "danger")
        return redirect(url_for("admin.listar_usuarios"))
    usuario.activo = False
    db.session.commit()
    flash(f"Usuario {usuario.nombre} desactivado.", "success")
    return redirect(url_for("admin.listar_usuarios"))


def _validar_usuario(form, exclude_id, es_creacion):
    nombre = form.get("nombre", "").strip()
    email = form.get("email", "").strip()
    rol = form.get("rol", "")
    password = form.get("password", "")
    confirmar = form.get("confirmar", "")
    if not nombre:
        return "El nombre es obligatorio."
    if not email:
        return "El correo electrónico es obligatorio."
    if "@" not in email or "." not in email.partition("@")[2]:
        return "El correo electrónico no tiene un formato válido."
    if rol not in ROLES_USUARIO:
        return "Selecciona un rol válido."
    stmt = select(Usuario).where(Usuario.email == email)
    if exclude_id:
        stmt = stmt.where(Usuario.id != exclude_id)
    if db.session.execute(stmt).scalars().first():
        return f"Ya existe un usuario con el correo {email}."
    if es_creacion and not password:
        return "La contraseña es obligatoria."
    if password and password != confirmar:
        return "Las contraseñas no coinciden."
    return None
