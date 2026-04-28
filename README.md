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
├── controllers/   # Blueprints: auth, admin, maintenance, reports
├── models/        # Modelos SQLAlchemy
├── services/      # Motor de predicción de vencimientos
└── templates/     # Jinja2 + Bootstrap 5.3
```
