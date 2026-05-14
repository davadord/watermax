# Arquitectura del sistema

---

## Resumen

Watermax es una aplicación web monolítica con patrón **Application Factory** (Flask).
La lógica de negocio vive en una capa de servicios separada de las rutas (blueprints).
El acceso a datos usa SQLAlchemy 2.0 exclusivamente.

```
Navegador → Flask (blueprints) → Services → SQLAlchemy 2.0 → MySQL 8
                                     ↕
                               WeasyPrint (PDF)
```

---

## Entry points

| Archivo | Contexto | Qué hace |
|---------|----------|----------|
| `run.py` | Desarrollo (Windows) | Inyecta PATH GTK condicionalmente (`os.path.isdir`), llama `create_app("development")` |
| `wsgi.py` | Producción (PythonAnywhere) | Expone `application = create_app("production")`. Sin código Windows-específico |

**Nota GTK/WeasyPrint:**
- Windows: `run.py` inyecta `C:\Program Files\GTK3-Runtime Win64\bin` en PATH solo si el
  directorio existe. Condicional — no falla si GTK no está instalado al arrancar.
- Linux/PythonAnywhere: las librerías GTK se instalan vía `apt`. No se requiere inyección.

---

## Application Factory (`app/__init__.py`)

```python
create_app(config_name="default")
```

Secuencia de inicialización:
1. Carga configuración desde `config[config_name]`.
2. En modo `production`: valida que `SECRET_KEY` y `SQLALCHEMY_DATABASE_URI` estén definidas.
   Lanza `RuntimeError` si faltan.
3. Inicializa extensiones: `SQLAlchemy`, `LoginManager`, `Migrate`, `CSRFProtect`.
4. Registra los cuatro blueprints.
5. Registra ruta raíz `/` → redirige a `reports.dashboard`.
6. Registra `context_processor` global (`inject_globals`).
7. Registra `errorhandler` para 404 y 500.

**Context processor `inject_globals`** (disponible en todos los templates):
- `is_admin`: `True` si el rol es `propietario` o `administrativo`.
- `alertas_count`: número de equipos con urgencia `vencido`. Se calcula llamando a
  `get_equipos_criticos()` **solo** cuando `request.endpoint` empieza con `"reports."`.
  En todas las demás rutas, vale `0` sin ejecutar la query.

---

## Configuración (`config.py`)

| Clase | Activada por | `DEBUG` | `DATABASE_URL` fallback | `SECRET_KEY` fallback |
|-------|--------------|---------|------------------------|----------------------|
| `DevelopmentConfig` | `run.py` / default | True | `mysql://root:password@localhost/watermax_db` | `"dev-secret-key"` |
| `ProductionConfig` | `wsgi.py` | False | None (requiere var de entorno) | None (requiere var de entorno) |

Variables de entorno requeridas en producción: `SECRET_KEY`, `DATABASE_URL`.

---

## Blueprints

### `/auth` — `app/blueprints/auth.py`

Rutas: `GET/POST /auth/login`, `GET /auth/logout`.

Lógica de bloqueo: incrementa `Usuario.intentos_fallidos` en cada fallo; bloquea la cuenta
hasta `bloqueado_hasta` (datetime) si supera el umbral.

### `/admin` — `app/blueprints/admin.py`

CRUD completo para: `Zona`, `Cliente`, `TipoEquipo`, `Componente`, `EquipoInstalado`.

Rutas de escritura protegidas con `@login_required` + `@role_required("propietario", "administrativo")`.

Flujo guiado equipo desde cliente: al crear un equipo, la URL puede incluir `?cliente_id=X`.
El formulario muestra el cliente como texto fijo con `<input hidden>`. Sin parámetro, muestra
el select completo.

### `/maintenance` — `app/blueprints/maintenance.py`

Rutas:
- `GET/POST /maintenance/nuevo/<equipo_id>` — registro de mantenimiento
- `GET /maintenance/equipo/<id>` — historial por equipo (paginado, 20/página)
- `GET /maintenance/cliente/<id>` — historial agrupado por equipo

**Transacción atómica en nuevo mantenimiento:**
1. `db.session.add(mant)` + `db.session.flush()` (obtiene `mant.id` sin commitear).
2. Crea todos los `DetalleMantenimiento`.
3. Si no hay ningún detalle, `db.session.rollback()` + flash error.
4. Si hay detalles, `db.session.commit()`.

Para cada componente con `accion == "reemplazo"`, llama a `calcular_proximo_componente()`
y guarda `proximo_mantenimiento` en `DetalleMantenimiento`.

### `/reports` — `app/blueprints/reports.py`

Rutas:
- `GET /reports/dashboard` — vista principal con cards resumen y tabla por zona
- `GET /reports/criticos` — equipos críticos con filtros zona/urgencia
- `GET /reports/zona/<id>/pdf` — PDF de zona (acepta `?fecha=YYYY-MM-DD`)
- `GET /reports/cliente/<id>/pdf` — PDF de cliente (historial completo + proyección)

Import de WeasyPrint siempre **lazy** (dentro de la función de ruta, no al top del módulo)
para que la app arranque correctamente en entornos sin GTK.

Cada ruta PDF tiene `try/except Exception → abort(503)` para errores de generación.

---

## Capa de servicios

### `app/services/prediction_service.py` — Motor predictivo

**Constantes:**
- `URGENCIA_VENCIDO = "vencido"` — días_restantes < 0
- `URGENCIA_PROXIMO = "proximo"` — 0 ≤ días_restantes ≤ 15
- `URGENCIA_EN_PLAZO = "en_plazo"` — días_restantes > 15
- `UMBRAL_ALERTA_DIAS = 15`

**`_intervalo_efectivo(equipo, componente)` → `(intervalo_dias, fuente, ultima_fecha)`**

Privada. Determina el intervalo de mantenimiento efectivo:
1. Consulta el historial de reemplazos del componente en el equipo
   (SQLAlchemy 2.0: `select + join + where accion="reemplazo" + order_by fecha`).
2. Si `equipo.fecha_reactivacion` existe, filtra fechas anteriores a ella.
3. Si hay ≥ 2 ciclos y la desviación del promedio respecto al nominal es ≤ 50%:
   retorna `(promedio_histórico_días, "historico", última_fecha_reemplazo)`.
4. Si no: retorna `(intervalo_nominal_meses × 30, "nominal", última_fecha_reemplazo)`.

**`calcular_vencimientos(equipo, fecha_ref=None)` → `list[dict]`**

Por cada `TipoEquipoComponente` del equipo:
- Llama a `_intervalo_efectivo`.
- `fecha_base` = `fecha_reactivacion` si existe, sino `fecha_instalacion`.
- `ultima_fecha` = última fecha de reemplazo si hay, sino `fecha_base`.
- `fecha_proyectada` = `ultima_fecha + timedelta(intervalo_dias)`.
- Clasifica urgencia. Retorna lista ordenada por (urgencia, dias_restantes).

Retorna: `[{componente, fecha_proyectada, urgencia, dias_restantes, intervalo_usado, fuente}, ...]`

**`calcular_proximo_componente(equipo, componente, fecha_intervencion)` → `date`**

Usado en `maintenance.py` al registrar un reemplazo.
Retorna `fecha_intervencion + intervalo_efectivo`. Excluye la intervención actual del cálculo
(aún no está commiteada cuando se llama).

**`get_equipos_criticos(zona_id=None, urgencia=None)` → `list[dict]`**

Carga todos los `EquipoInstalado` activos con `joinedload` encadenado para evitar N+1:
`tipo_equipo → componentes → componente`, más `zona` y `cliente`.

Filtra opcionalmente por `zona_id` y/o `urgencia`.

Retorna: `[{equipo, urgencia_maxima, dias_min, componentes_criticos: [...]}, ...]`

Solo incluye equipos con al menos un componente en estado `vencido` o `proximo`.

### Convenciones de carga de relaciones

| Estrategia | Cuándo usarla | Nota |
|---|---|---|
| `selectinload` | Padre fijo, cargar sus hijos en SELECTs adicionales eficientes | Historial de un equipo, detalles de un mantenimiento |
| `joinedload` | Todos los hijos de un padre en un solo JOIN | Equipos de un cliente con sus relaciones. Requiere `.unique()` antes de `.scalars()` |

**Paginación:** usar `db.paginate(stmt, page=p, per_page=20, error_out=False)`. La API `Model.query.paginate()` es legacy (SQLAlchemy 1.x). `error_out=False` evita 404 en páginas fuera de rango.

### `app/services/report_service.py` — Datos para PDFs

**`get_reporte_zona(zona_id, fecha=None)` → `dict`**

Carga equipos activos de la zona con joinedload. Calcula vencimientos con `fecha_ref`.
Construye resumen `{total, vencidos, proximos, en_plazo}`. Ordena por severidad.

Retorna: `{zona, items: [{equipo, vencimientos, n_vencidos, n_proximos}], resumen, fecha_ref, fecha_generacion}`

**`get_reporte_cliente(cliente_id)` → `dict`**

Carga equipos activos del cliente. Por cada equipo, carga historial completo de mantenimientos
(con detalles y técnico) y proyección de vencimientos.

Retorna: `{cliente, items: [{equipo, historial, proyeccion}], fecha_generacion}`

---

## Modelos de datos

```
zonas
  id, nombre (unique), descripcion

clientes
  id, nombre, tipo_identificador (Enum), identificador (unique NOT NULL),
  telefono, direccion, email, activo, creado_en

equipos_instalados
  id, cliente_id → clientes, zona_id → zonas, tipo_equipo_id → tipos_equipo,
  sector, numero_serie, fecha_instalacion, fecha_reactivacion (nullable), activo

tipos_equipo
  id, nombre, marca, descripcion

componentes
  id, nombre, descripcion, intervalo_nominal (Integer, meses enteros)

tipo_equipo_componente     ← tabla de unión N:M pura
  id, tipo_equipo_id → tipos_equipo, componente_id → componentes

mantenimientos
  id, equipo_id → equipos_instalados, tecnico_id → usuarios,
  fecha, observaciones, completado, creado_en

detalles_mantenimiento
  id, mantenimiento_id → mantenimientos, componente_id → componentes,
  accion (Enum: reemplazo|limpieza|revision),
  notas, proximo_mantenimiento (Date, nullable, indexed)

usuarios
  id, nombre, email (unique), password_hash (bcrypt),
  rol (Enum: propietario|administrativo|tecnico),
  activo, intentos_fallidos, bloqueado_hasta (nullable)
```

**Relaciones backref clave:**
- `Cliente.equipos` → lista de `EquipoInstalado` (backref `"cliente"`)
- `EquipoInstalado.cliente` — accesible vía backref definido en `Client.equipos`
- `EquipoInstalado.zona` — relationship directo en `equipment.py`
- `EquipoInstalado.tipo_equipo` — relationship directo
- `TipoEquipo.componentes` → lista de `TipoEquipoComponente`
- `Mantenimiento.detalles` → lista de `DetalleMantenimiento`

**Decisiones de modelo** — ver `docs/decisions.md` para el razonamiento completo.

---

## Auth y control de acceso

**Roles:** `propietario`, `administrativo`, `tecnico`.

**`@login_required`** (Flask-Login) — siempre primero.

**`@role_required(*roles)`** (`app/utils/decorators.py`) — siempre después de `@login_required`.
Retorna template `errors/403.html` con status 403 si el rol no coincide.

**`is_admin`** (context processor) — `True` para `propietario` y `administrativo`.
Controla visibilidad de elementos de admin en templates sin necesidad de import.

**CSRF:** `Flask-WTF CSRFProtect` activo globalmente. Todo form POST tiene token CSRF.

**Contraseñas:** bcrypt (`py-bcrypt`). `set_password()` y `check_password()` en `Usuario`.

---

## Generación de PDFs

WeasyPrint 68.1 + GTK3.

Templates PDF standalone (`reports/pdf_zona.html`, `reports/pdf_cliente.html`) con CSS inline.
No heredan de `base.html` para evitar dependencias de estáticos externos.

WeasyPrint maneja paginación automática a partir del CSS de los templates.

Flujo en cada ruta PDF:
```python
from weasyprint import HTML          # import lazy
html = render_template("...", **datos)
try:
    pdf = HTML(string=html).write_pdf()
except Exception:
    abort(503)
return Response(pdf, mimetype="application/pdf", ...)
```

---

## Base de datos y migraciones

**Motor:** MySQL 8, charset `utf8mb4_unicode_ci`.
**Versiones Alembic:** 3 migraciones aplicadas.

**Instalación inicial en servidor nuevo:**
```bash
python setup_db.py        # db.create_all() + datos iniciales
flask db stamp head       # marcar migraciones como aplicadas sin ejecutarlas
```
**No usar** `flask db upgrade` en BD vacía — la cadena Alembic no puede crear el schema inicial.

**Cambios de esquema posteriores:**
```bash
flask db migrate -m "descripcion"
flask db upgrade
```

**DDL en MySQL es auto-commit.** Cada `ALTER TABLE`, `ADD COLUMN`, `DROP COLUMN` hace COMMIT implícito — no hay rollback si la migración falla a mitad. Si una migración mueve un campo entre tablas en un solo paso y el segundo falla, la BD queda inconsistente. Patrón seguro: (1) ADD COLUMN nullable, (2) UPDATE datos, (3) ALTER NOT NULL, (4) DROP COLUMN original. En dev, si hay inconsistencia: recrear con `python setup_db.py`.

---

## Frontend

- Bootstrap 5.3 (CDN) + Jinja2.
- `app/static/css/app.css`: tokens de diseño y clases utilitarias propias.
- `app/static/js/app.js`: tooltips Bootstrap, modal confirm global, toggle contraseña,
  filter reset, submit guard (previene doble submit).
- `app/templates/_macros.html`: macros Jinja2 reutilizables:
  `page_header`, `empty_state`, `delete_button`, `confirm_button`, `icon_link`,
  `field_value`, `field_selected`, `field_checked`.

---

## Usuarios de prueba

| Email | Rol | Clave |
|-------|-----|-------|
| admin@watermax.ec | propietario | Watermax2026! |
| admin2@watermax.ec | administrativo | Watermax2026! |
| tecnico@watermax.ec | tecnico | Watermax2026! |
