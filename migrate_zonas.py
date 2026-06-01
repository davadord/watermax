"""
Migrar nombres de zonas para reflejar la geografía real de Guayaquil.

Antes (5 zonas):  Norte · Sur · Centro · Este · Oeste
Después (6 zonas): Norte · Centro-Norte · Noroeste · Centro · Centro-Sur · Sur

Cambios:
  Este  → Centro-Sur   (renombrar, equipos existentes se conservan)
  Oeste → Noroeste     (renombrar, equipos existentes se conservan)
  Centro-Norte         (crear — zona nueva, sin equipos inicialmente)

Uso:
    python migrate_zonas.py              # development (local)
    python migrate_zonas.py production   # PythonAnywhere
"""
import sys
from sqlalchemy import select
from app import create_app, db
from app.models.client import Zona

CONFIG = sys.argv[1] if len(sys.argv) > 1 else "development"
app = create_app(CONFIG)

RENOMBRAR = {
    "Este":  "Centro-Sur",
    "Oeste": "Noroeste",
}
CREAR = ["Centro-Norte"]


def main():
    with app.app_context():
        zonas = {z.nombre: z for z in db.session.execute(select(Zona)).scalars().all()}
        cambios = 0

        for viejo, nuevo in RENOMBRAR.items():
            if viejo not in zonas:
                print(f"  Omitido: '{viejo}' no existe.")
                continue
            if nuevo in zonas:
                print(f"  Omitido: '{nuevo}' ya existe, no se renombra '{viejo}'.")
                continue
            zonas[viejo].nombre = nuevo
            print(f"  Renombrado: '{viejo}' → '{nuevo}'")
            cambios += 1

        for nombre in CREAR:
            if nombre in zonas:
                print(f"  Omitido: '{nombre}' ya existe.")
                continue
            db.session.add(Zona(nombre=nombre))
            print(f"  Creada: '{nombre}'")
            cambios += 1

        if cambios:
            db.session.commit()
            print(f"\nMigración completa: {cambios} cambio(s) aplicado(s).")
        else:
            print("\nNada que migrar — BD ya está al día.")

        zonas_final = db.session.execute(
            select(Zona).order_by(Zona.nombre)
        ).scalars().all()
        print("\nZonas resultantes:")
        for z in zonas_final:
            print(f"  id={z.id:<3} {z.nombre}")


if __name__ == "__main__":
    main()
