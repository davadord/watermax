"""
Entry point para PythonAnywhere (y cualquier servidor WSGI compatible).

DESPLIEGUE INICIAL EN PYTHONANYWHERE
=====================================
1. Clonar/subir el repo al directorio del proyecto.
2. Crear virtualenv e instalar dependencias:
       pip install -r requirements.txt
3. Configurar variables de entorno en el panel de PA (o en .env):
       SECRET_KEY=<clave-aleatoria-larga>
       DATABASE_URL=mysql://usuario:clave@host/nombre_db
4. Inicializar la base de datos (solo la primera vez):
       python setup_db.py          # crea tablas + datos iniciales
       flask db stamp head         # marca migraciones como aplicadas
5. Para cambios de esquema futuros:
       flask db migrate -m "descripcion"
       flask db upgrade
6. En la consola web de PA, apuntar el fichero WSGI a este archivo
   y ajustar 'project_home' si la ruta no coincide.
"""
import sys
import os

project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import create_app

application = create_app("production")
