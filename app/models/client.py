from app import db
from datetime import datetime


class Zona(db.Model):
    __tablename__ = "zonas"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False, unique=True)
    descripcion = db.Column(db.String(200))

    def __repr__(self):
        return f"<Zona {self.nombre}>"


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(250))
    email = db.Column(db.String(120))
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    equipos = db.relationship("EquipoInstalado", backref="cliente", lazy=True)

    def __repr__(self):
        return f"<Cliente {self.nombre}>"
