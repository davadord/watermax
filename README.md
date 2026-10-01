# Watermax — Sistema de gestión de mantenimiento preventivo

Aplicación web para la gestión de mantenimiento de purificadores de agua, orientada a operaciones de clientes, zonas, equipos, mantenimientos y reportes de vencimientos.

Estado actual: proyecto finalizado y validado en la fase de cierre del Sprint 5, con despliegue de preproducción en PythonAnywhere y documentación técnica completa en la carpeta docs.

Stack:
- Python 3.13
- Flask 3.x
- SQLAlchemy 2.x
- MySQL 8
- Bootstrap 5.3
- Flask-Login, Flask-WTF, Flask-Migrate
- WeasyPrint 68.1 + reportlab

---

## Estado del proyecto

El sistema ya está implementado y funcionando con los siguientes entregables clave:

- Autenticación con bloqueo por intentos fallidos
- CRUD completo de clientes, zonas, equipos, tipos de equipo y componentes
- Gestión de usuarios con roles y reglas de negocio
- Registro, edición y anulación de mantenimientos
- Motor predictivo de vencimientos por componente
- Dashboard global con filtros por zona y alertas críticas
- Reportes PDF por zona y por cliente
- Páginas de error personalizadas
- Configuración preparada para producción con variables de entorno y WSGI

## Documentación técnica

- [docs/current-state.md](docs/current-state.md): estado vivo del proyecto, issues, riesgos y cierre del sprint
- [docs/architecture.md](docs/architecture.md): arquitectura, blueprints, modelos y servicios
- [docs/decisions.md](docs/decisions.md): decisiones técnicas y de producto tomadas
- [docs/produccion.md](docs/produccion.md): guía paso a paso de implementación inicial en PythonAnywhere
- [docs/actualizacion.md](docs/actualizacion.md): guía para actualizar una versión ya desplegada en PythonAnywhere

---

## Ejecución local

```bash
# 1. Clonar el repositorio
git clone https://github.com/davadord/watermax.git
cd watermax

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Crear base de datos en MySQL
# CREATE DATABASE watermax_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 5. Configurar variables de entorno
# Crear un archivo .env local con:
# SECRET_KEY=tu_clave_local
# DATABASE_URL=mysql://usuario:password@localhost/watermax_db

# 6. Iniciar la aplicación
python run.py
```

La aplicación queda disponible en http://127.0.0.1:5000

---

## Implementación en producción

La guía completa para desplegar la aplicación en un entorno real está en [docs/produccion.md](docs/produccion.md).

Resumen del flujo recomendado:

1. Preparar servidor Linux o PythonAnywhere con Python 3.13 y MySQL
2. Instalar dependencias del proyecto
3. Definir variables de entorno `SECRET_KEY` y `DATABASE_URL`
4. Ejecutar `python setup_db.py`
5. Ejecutar `flask db stamp head`
6. Apuntar el WSGI a `wsgi.py`
7. Verificar login, base de datos y generación de reportes PDF

---

## Estructura del proyecto

```text
watermax/
├── app/
│   ├── blueprints/
│   ├── models/
│   ├── services/
│   ├── static/
│   ├── templates/
│   └── utils/
├── docs/
├── migrations/
├── tests/
├── config.py
├── run.py
├── wsgi.py
├── setup_db.py
├── requirements.txt
├── README.md
└── AGENTS.md
```

---

## Resultado final

La aplicación alcanzó el cierre funcional del proyecto de titulación, con validación de requisitos, pruebas, documentación y preparación para despliegue en entorno real.

Se recomienda usar la guía de producción para una instalación segura y reproducible en un servidor de producción o en PythonAnywhere.
