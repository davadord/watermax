from app import db


class TipoEquipo(db.Model):
    __tablename__ = "tipos_equipo"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    marca = db.Column(db.String(80))
    descripcion = db.Column(db.String(250))
    componentes = db.relationship("TipoEquipoComponente", backref="tipo_equipo", lazy=True)
    equipos = db.relationship("EquipoInstalado", backref="tipo_equipo", lazy=True)


class Componente(db.Model):
    __tablename__ = "componentes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(200))
    unidad = db.Column(db.String(20), default="meses")
    tipos_equipo = db.relationship("TipoEquipoComponente", backref="componente", lazy=True)


class TipoEquipoComponente(db.Model):
    """Tabla de unión N:M con intervalo nominal por combinación."""
    __tablename__ = "tipo_equipo_componente"

    id = db.Column(db.Integer, primary_key=True)
    tipo_equipo_id = db.Column(db.Integer, db.ForeignKey("tipos_equipo.id"), nullable=False)
    componente_id = db.Column(db.Integer, db.ForeignKey("componentes.id"), nullable=False)
    intervalo_nominal = db.Column(db.Integer, nullable=False)


class EquipoInstalado(db.Model):
    __tablename__ = "equipos_instalados"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    tipo_equipo_id = db.Column(db.Integer, db.ForeignKey("tipos_equipo.id"), nullable=False)
    zona_id = db.Column(db.Integer, db.ForeignKey("zonas.id"), nullable=False)
    sector = db.Column(db.String(100))
    numero_serie = db.Column(db.String(80))
    fecha_instalacion = db.Column(db.Date, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    zona = db.relationship("Zona", backref="equipos")
    mantenimientos = db.relationship("Mantenimiento", backref="equipo", lazy=True)
