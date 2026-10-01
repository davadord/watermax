# Guía para actualizar cambios en producción en PythonAnywhere

Esta guía está pensada para una versión ya desplegada de Watermax en PythonAnywhere. Su objetivo es actualizar el código, aplicar cambios de configuración y publicar la nueva versión sin perder la base de datos ni la configuración operativa actual.

---

## 1. Objetivo

Actualizar la app en producción cuando ya existe una versión funcionando y se quiere publicar una nueva entrega con cambios en:

- lógica de negocio
- templates
- motores de predicción
- reportes PDF
- validaciones o permisos
- correcciones menores or mayores

La estrategia recomendada es:

1. respaldar la base y la configuración
2. actualizar el código desde Git
3. instalar dependencias si hace falta
4. aplicar migraciones si el esquema cambió
5. recargar la web app
6. verificar servicios críticos

---

## 2. Requisitos previos

Antes de actualizar, confirmar:

- que la aplicación ya está corriendo en PythonAnywhere
- que la URL de producción responde correctamente
- que tienes acceso a la consola Bash del proyecto
- que conoces el usuario y la base de datos de producción
- que los cambios han sido probados localmente antes de subirlos

Se recomienda siempre hacer una copia de seguridad de la base de datos antes de un despliegue con cambios estructurales.

---

## 3. Hacer respaldo antes de actualizar

Desde la consola de PythonAnywhere:

```bash
cd ~/watermax
source venv/bin/activate
```

Si existe acceso a MySQL, hacer un dump de la base de datos antes de cualquier cambio importante:

```bash
mysqldump -u <usuario> -p <nombre_db> > backup_watermax_$(date +%F_%H%M%S).sql
```

Si la base de datos es gestionada por PythonAnywhere, también es útil guardar un export local o un respaldo en una carpeta del proyecto o en la nube.

> Para una actualización rutinaria sin cambios de esquema, esta copia es una medida de seguridad y no reemplaza la validación posterior.

---

## 4. Actualizar el código desde Git

Dentro del directorio del proyecto:

```bash
cd ~/watermax
git pull origin main
```

Si el repositorio usa otra rama, reemplazar `main` por la rama correcta:

```bash
git pull origin <nombre_rama>
```

Si el proyecto aún no está asociado al remoto correcto, revisar antes:

```bash
git remote -v
```

---

## 5. Instalar dependencias si hubo cambios

Si el cambio incluye paquetes nuevos o actualizaciones de librerías, entrar al entorno virtual y reinstalar:

```bash
cd ~/watermax
source venv/bin/activate
pip install -r requirements.txt
```

Esto es importante si:

- hubo cambio en `requirements.txt`
- se añadió nueva dependencia
- el proyecto fue actualizado desde una rama con cambios de entorno

---

## 6. Revisar variables de entorno

Las variables de entorno de producción no se actualizan desde el repositorio. Deben mantenerse en el panel de PythonAnywhere.

Revisar que sigan presentes:

```text
SECRET_KEY=...
DATABASE_URL=mysql://.../...
```

Si un cambio de entorno exige valores nuevos, editarlos desde:

- `PythonAnywhere → Web → tu app → Environment variables`

No mover credenciales manualmente al repositorio ni al código.

---

## 7. Actualizar esquema de base de datos si aplica

### Caso A: solo hay cambios de código, sin cambios estructurales

No hace falta migrar la base. Solo hacer reload de la app y validar funcionamiento.

### Caso B: hubo cambios en los modelos o en la estructura de la base

Primero revisar si el proyecto usa migraciones con Flask-Migrate.

Ejemplo de flujo recomendado:

```bash
cd ~/watermax
source venv/bin/activate
flask db migrate -m "descripcion del cambio"
flask db upgrade
```

### Importante

Si la base aún está vacía o no se ha inicializado antes, el flujo correcto sigue siendo:

```bash
python setup_db.py
flask db stamp head
```

Nunca usar `flask db upgrade` como paso inicial sobre una base nueva vacía.

---

## 8. Recargar la web app en PythonAnywhere

Una vez actualizado el código y verificados los cambios de entorno y BD:

1. ir a `PythonAnywhere → Web`
2. abrir la app de Watermax
3. pulsar `Reload`

Esto fuerza a la web app a cargar la nueva versión del proyecto.

Si el reload falla, revisar:

- logs de error
- `wsgi.py`
- `Environment variables`
- que el virtualenv esté bien apuntado

---

## 9. Verificación post-despliegue

Después del reload, comprobar los puntos críticos del sistema:

### 9.1 Login

- abrir la URL pública
- ingresar con un usuario válido
- confirmar que la sesión funciona

### 9.2 Dashboard

- revisar el dashboard principal
- comprobar que carga estado global y filtros
- revisar que no haya errores de template o variable no definida

### 9.3 Mantenimientos

- crear o editar un mantenimiento
- verificar que el cálculo predictivo sigue funcionando
- confirmar que el historial se actualiza correctamente

### 9.4 Reportes PDF

- generar un PDF por zona
- generar un PDF por cliente
- confirmar que la salida no falla ni devuelve error 500/503

### 9.5 Errores y logs

Revisar el error log de PythonAnywhere para detectar:

- `RuntimeError`
- `NameError`
- `ImportError`
- problemas de MySQL
- errores con WeasyPrint/reportlab

---

## 10. Actualización de cambios sin perder trabajo

Si la actualización genera errores, el flujo recomendado es:

```bash
cd ~/watermax
git log --oneline -n 5
```

Para volver a una versión anterior:

```bash
git checkout <hash_anterior>
```

Luego, recargar la app y verificar si la versión previa funciona.

En cambios fuertes de estructura, siempre revisar antes si la BD necesita rollback o restauración desde el respaldo.

---

## 11. Buenas prácticas para despliegues en PA

- no hacer cambios de SQL sin respaldo previo
- no modificar `SECRET_KEY` ni `DATABASE_URL` desde el repositorio
- no publicar cambios que no hayan sido revisados localmente
- revisar logs justo después del reload
- hacer pruebas mínimas del flujo principal antes de cerrar la actualización

---

## 12. Flujo resumido

El proceso general es este:

```bash
cd ~/watermax
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
# si hubo cambio de esquema:
flask db migrate -m "descripcion"
flask db upgrade
# luego recargar la app desde PythonAnywhere
```

Y luego verificar:

- login
- dashboard
- registros y cálculos
- PDF
- logs

---

## 13. Resultado esperado

Con este procedimiento, una versión ya implementada en PythonAnywhere puede actualizarse de forma segura y sin reiniciar todo el proyecto desde cero. El despliegue queda controlado, con mejor trazabilidad y menos riesgo de romper la app en producción.

Este flujo es ideal para un entorno donde el sistema ya está en línea y solo se necesita publicar una nueva entrega con cambios funcionales o correcciones operativas.
