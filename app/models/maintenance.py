from app import db
from datetime import datetime


class Mantenimiento(db.Model):
    __tablename__ = "mantenimientos"

    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey("equipos_instalados.id"), nullable=False)
    tecnico_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    observaciones = db.Column(db.Text)
    completado = db.Column(db.Boolean, default=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    detalles = db.relationship("DetalleMantenimiento", backref="mantenimiento", lazy=True)
    tecnico = db.relationship("Usuario", foreign_keys=[tecnico_id])


class DetalleMantenimiento(db.Model):
    __tablename__ = "detalles_mantenimiento"

    id = db.Column(db.Integer, primary_key=True)
    mantenimiento_id = db.Column(db.Integer, db.ForeignKey("mantenimientos.id"), nullable=False)
    componente_id = db.Column(db.Integer, db.ForeignKey("componentes.id"), nullable=False)
    accion = db.Column(db.Enum("reemplazo", "limpieza", "revision"), nullable=False)
    notas = db.Column(db.String(200))
    componente = db.relationship("Componente", foreign_keys=[componente_id])
