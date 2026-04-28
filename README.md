# Watermax — Sistema de Gestión de Mantenimiento

Aplicación web para la gestión de mantenimiento preventivo de purificadores de agua.  
Stack: **Python 3.11 · Flask 3.x · SQLAlchemy 2.x · MySQL 8.x · Bootstrap 5.3**

---

## Estructura del proyecto

```
watermax/
├── app/
│   ├── __init__.py            # Application factory
│   ├── controllers/           # Blueprints (auth, admin, maintenance, reports)
│   ├── models/                # Modelos SQLAlchemy
│   ├── services/              # prediction_service.py (motor de vencimientos)
│   ├── static/                # CSS y JS personalizados
│   └── templates/             # Jinja2 (base, auth, admin, maintenance, reports)
├── migrations/                # Flask-Migrate
├── tests/                     # Pruebas unitarias
├── docs/                      # Diagramas UML y documentación
├── config.py
├── run.py
├── setup_db.py                # Inicialización de BD + datos semilla
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Instalación local (primera vez)

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/watermax.git
cd watermax
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear la base de datos en MySQL

```sql
CREATE DATABASE watermax_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tu usuario y contraseña de MySQL
```

### 6. Inicializar tablas y datos semilla

```bash
python setup_db.py
```

### 7. Arrancar el servidor de desarrollo

```bash
flask run
# o
python run.py
```

Abre `http://127.0.0.1:5000`

**Credenciales iniciales:**  
Email: `admin@watermax.ec`  
Password: `Watermax2026!`  
⚠️ Cambia la contraseña antes de desplegar en producción.

---

## Flujo de desarrollo (Scrum — sprints de 2 semanas)

| Sprint | Módulo | Descripción |
|--------|--------|-------------|
| 0 | Setup | Entorno local, repositorio, estructura base |
| 1 | Auth + Admin | Login, CRUD clientes, zonas, equipos |
| 2 | Mantenimientos | Registro de órdenes de trabajo y componentes |
| 3 | Predicción | Motor `prediction_service.py` + dashboard |
| 4 | Reportes PDF | WeasyPrint, reporte diario por zona |
| 5 | Pruebas | JMeter (rendimiento) + SUS (usabilidad) |

---

## Despliegue en PythonAnywhere

1. Subir el proyecto vía Git o ZIP.
2. Crear entorno virtual en la consola de PythonAnywhere.
3. Configurar una app Web WSGI apuntando a `run.py`.
4. Crear la BD MySQL desde el panel y actualizar `DATABASE_URL` en `.env`.
5. Ejecutar `python setup_db.py` desde la consola.

---

## Herramientas de validación

- **Pruebas de rendimiento:** Apache JMeter — simular carga con 4 usuarios concurrentes.
- **Usabilidad:** Escala SUS (System Usability Scale) — meta ≥ 68 puntos.
- **Calidad:** ISO/IEC 25010 — eficiencia de rendimiento y usabilidad.
