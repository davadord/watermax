# Watermax — Sistema de Gestión de Mantenimiento

Aplicación web para la gestión de mantenimiento preventivo de purificadores de agua.  
Stack: **Python 3.13 · Flask 3.x · SQLAlchemy 2.x · MySQL 8.x · Bootstrap 5.3**

---

## Instalación local

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
cp .env.example .env
# Editar .env con tus credenciales de MySQL

# 6. Arrancar el servidor
python run.py
```

Abre `http://127.0.0.1:5000`

---

## Estructura

```
app/
├── blueprints/    # auth, admin, maintenance, reports
├── models/        # SQLAlchemy: client, equipment, maintenance, user
├── services/      # Motor predictivo de vencimientos (prediction_service.py)
└── templates/     # Jinja2 + Bootstrap 5.3
```

---

## Funcionalidades implementadas

- Autenticación con bloqueo por intentos fallidos
- CRUD completo: clientes, zonas, equipos instalados, tipos de equipo, componentes
- Gestión de usuarios: alta, edición, desactivación (roles propietario/administrativo/tecnico)
- Registro y edición de mantenimientos; anulación con motivo (soft delete)
- Motor predictivo: proyección de vencimientos por componente (algoritmo histórico/nominal)
- Dashboard global con resumen por zona; caché cross-request con TTL 60 s
- Vista de equipos críticos con filtros zona/urgencia
- Reportes PDF por zona (reportlab) y por cliente (WeasyPrint)
- Páginas de error personalizadas (403/404/500)
- Despliegue en PythonAnywhere: https://dordonezm2.pythonanywhere.com/

---

## Estado de desarrollo

| Sprint | Período | Issues | Estado |
|--------|---------|--------|--------|
| S0 | abr 2026 | Entorno, modelos, auth, dashboard | Completado |
| S1 | abr–may 2026 | #2 #3 #4 #5 #6 #24 — CRUD clientes, zonas, equipos | Completado |
| S2 | may 2026 | #21 #22 #7 #8 #9 #25 — Registro mantenimientos, motor predictivo | Completado |
| S3 | may 2026 | #10 #11 #12 #23 #26 — Alertas críticas, dashboard global, motor refinado | Completado |
| S4 | may 2026 | #13 #14 #15 — report_service.py, reportes PDF | Completado |
| S5 | may–jul 2026 | #18 (deploy), #29 (listado mantenimientos), #16+#30 (perf), #31 (tests), #32 (usuarios) — cerrados. #17 (SUS) en curso | **En curso** |
