# Guía de implementación en producción para PythonAnywhere

Esta guía está orientada a la entrega real del proyecto en PythonAnywhere, con el flujo que ya quedó validado para la aplicación Watermax.

La aplicación está preparada para producción con `config.py` y `wsgi.py`:

- `create_app("production")` usa `ProductionConfig`
- `SECRET_KEY` y `DATABASE_URL` son obligatorias
- `wsgi.py` expone la app para el servidor WSGI de PythonAnywhere

---

## 1. Requisitos del entorno de PythonAnywhere

Antes de subir el proyecto, preparar lo siguiente:

- Cuenta activa en PythonAnywhere
- Plan compatible con la app (en el proyecto se usó plan Developer)
- Base de datos MySQL disponible desde PythonAnywhere
- Acceso al dashboard de la cuenta para configurar variables de entorno y web app

La estructura del despliegue objetivo es la siguiente:

- Código del proyecto: carpeta del repositorio en el home del usuario
- Entorno virtual: creado en PythonAnywhere
- Base de datos: MySQL gestionada por PythonAnywhere o por la instancia configurada para el proyecto
- WSGI: apuntando a `wsgi.py`

---

## 2. Subir el proyecto a PythonAnywhere

### Opción recomendada

Desde la consola Bash de PythonAnywhere:

```bash
cd ~
git clone <url-del-repositorio> watermax
cd watermax
```

Si el proyecto ya está subido, verificar la estructura:

```bash
ls
```

Debe aparecer algo como:

- `app/`
- `docs/`
- `migrations/`
- `config.py`
- `run.py`
- `wsgi.py`
- `setup_db.py`
- `requirements.txt`

---

## 3. Crear el entorno virtual en PA

En la consola de PythonAnywhere:

```bash
cd ~/watermax
python3.13 -m venv venv
source venv/bin/activate
```

Luego instalar dependencias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Importante sobre dependencias

El proyecto usa:

- Flask 3.x
- SQLAlchemy 2.x
- mysqlclient
- Flask-Migrate
- bcrypt
- WeasyPrint 68.1
- reportlab

Estas dependencias están declaradas en `requirements.txt` y deben instalarse en el entorno de production de PA.

---

## 4. Crear la base de datos MySQL

Desde el panel de PythonAnywhere:

1. Ir a la sección de `Databases`
2. Crear una base de datos MySQL
3. Anotar:
   - nombre de la base
   - usuario
   - contraseña
   - host interno de MySQL

El valor final se usará en `DATABASE_URL`.

Ejemplo de formato esperado:

```text
mysql://<usuario>:<password>@<host>/<nombre_db>
```

Ejemplo real:

```text
mysql://dordonezm2:password@dordonezm2.mysql.pythonanywhere-services.com/dordonezm2$watermax_db
```

---

## 5. Configurar variables de entorno en PythonAnywhere

Entrar en el panel de PythonAnywhere y abrir la sección de la web app.

### Variables de entorno requeridas

Configurar estas dos variables obligatoriamente:

```text
SECRET_KEY=una_clave_larga_y_aleatoria
DATABASE_URL=mysql://usuario:password@host/nombre_base
```

En el dashboard de PythonAnywhere, esto se hace en:

- `Web`
- abrir la aplicación
- `Environment variables`
- agregar ambas variables

### Recomendación

Usar una clave fuerte, por ejemplo:

```text
SECRET_KEY=9f8c2a1d... (longitud suficiente y aleatoria)
```

No guardar esta clave en el repositorio ni en archivos versionados.

---

## 6. Inicializar la base de datos

En la consola de PythonAnywhere, dentro del repositorio:

```bash
cd ~/watermax
source venv/bin/activate
python setup_db.py
flask db stamp head
```

### ¿Por qué este orden?

Porque en un servidor nuevo la base de datos no está creada todavía. `setup_db.py` crea las tablas del modelo actual. Luego `flask db stamp head` marca las migraciones existentes como ya aplicadas sin intentar ejecutar un upgrade sobre una base aún vacía.

> Regla clave: en una base nueva, usar `setup_db.py` + `flask db stamp head`. No usar `flask db upgrade` como primer paso.

---

## 7. Configurar la web app en PythonAnywhere

### 7.1 Abrir configuración de la web app

En `Web`:

1. Click en `Add a new web app`
2. Elegir manual configuration
3. Seleccionar Python 3.13
4. Elegir la URL pública del sitio

### 7.2 Configurar el directorio del proyecto

En la web app configurar:

- `Source code`: `/home/<usuario>/watermax`
- `Working directory`: `/home/<usuario>/watermax`
- `Virtualenv`: `/home/<usuario>/watermax/venv`

### 7.3 Configurar el WSGI file

El archivo WSGI ya está preparado en:

```text
/var/www/<usuario>_pythonanywhere_com_wsgi.py
```

Debe apuntar a la app en producción. El contenido recomendado es el que ya viene en `wsgi.py`:

```python
import sys
import os

project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import create_app

application = create_app("production")
```

> En PythonAnywhere, esto se edita desde el panel del WSGI file, no dentro del repositorio.

### 7.4 Reiniciar la app

Una vez guardado:

- pulsar `Reload`
- revisar si la página responde en la URL pública

---

## 8. Verificar que la app está funcionando

Tras el reload, validar los siguientes puntos:

### Login

- abrir la URL pública
- intentar ingresar con un usuario válido
- verificar que la sesión funciona

### Dashboard

- confirmar que se cargan cards y resumen de equipos
- verificar filtros por zona

### Registro de mantenimientos

- crear un cliente
- crear un equipo
- registrar un mantenimiento
- confirmar que el motor predictivo calcula fechas de vencimiento correctamente

### Reportes PDF

- generar un PDF por zona
- generar un PDF por cliente
- comprobar que no hay errores 500 ni 503

---

## 9. Consideraciones de producción específicas de PA

### WeasyPrint y librerías del sistema

PythonAnywhere ya tiene el entorno base para ejecutar Flask, pero hay que revisar que la app pueda generar PDF sin errores. Si el PDF falla:

- revisar logs de error
- confirmar que las dependencias están instaladas
- verificar que `wsgi.py` usa `create_app("production")`

### Variables de entorno

No dejar valores sensibles en:

- `README.md`
- código fuente
- archivos de configuración de repositorio

Todo secreto debe ir en el panel de variables de entorno de PythonAnywhere.

### Logs y diagnóstico

En PythonAnywhere se revisan estos archivos:

- error log
- server log
- console output de la app

Para detectar fallos de importación, base de datos o PDF.

---

## 10. Flujo recomendado para futuros cambios

Cuando se haga un cambio de esquema o de datos en producción, usar:

```bash
cd ~/watermax
source venv/bin/activate
flask db migrate -m "descripcion del cambio"
flask db upgrade
```

Solo usar esto cuando la base ya existe. En una instalación nueva, el proceso correcto sigue siendo:

```bash
python setup_db.py
flask db stamp head
```

---

## 11. Solución rápida de errores comunes

### Error: `RuntimeError: SECRET_KEY not configured`

Solución:

- agregar `SECRET_KEY` en `Environment variables`
- recargar la app

### Error: `DATABASE_URL not configured`

Solución:

- verificar que la cadena de conexión a MySQL esté correcta
- confirmar que la base existe y que el usuario tiene permisos

### Error 500 al generar PDF

Solución:

- revisar el log de errores
- confirmar que WeasyPrint está disponible en el entorno
- validar que la ruta de la app es la correcta y que el proyecto está activo

### Error al iniciar la app

Solución:

- revisar el WSGI file
- confirmar que `project_home` y la ruta del proyecto están correctos
- revisar si `application = create_app("production")` está bien definido

---

## 12. Resultado esperado en producción

Con esta configuración, Watermax queda operativo en PythonAnywhere con:

- autenticación segura
- conexión a MySQL
- app arrancando desde WSGI
- dashboard y gestión funcional
- reportes PDF funcionando
- despliegue reproducible y listo para uso real

Esta es la implementación que corresponde al estado final del proyecto y al despliegue validado para la fase de producción del trabajo de titulación.
